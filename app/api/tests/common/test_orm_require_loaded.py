import pytest
import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, create_engine
from sqlalchemy.orm import relationship, selectinload, joinedload, sessionmaker, DeclarativeBase

from agentops.common.orm import require_loaded


class ModelBase(DeclarativeBase):
    """Separate base for testing to avoid conflicts with main BaseModel."""
    pass


class AuthorModel(ModelBase):
    """Test model representing an author for integration testing."""
    __tablename__ = "test_authors"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    
    # Relationship to books
    books = relationship("BookModel", back_populates="author", lazy="raise")
    
    @require_loaded("books")
    def get_book_count(self):
        """Method that requires books to be loaded."""
        return len(self.books)
    
    @require_loaded("books")
    def get_book_titles(self):
        """Method that requires books to be loaded to access titles."""
        return [book.title for book in self.books]


class BookModel(ModelBase):
    """Test model representing a book for integration testing."""
    __tablename__ = "test_books"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    page_count = Column(Integer, default=100)
    author_id = Column(String, ForeignKey("test_authors.id"))
    
    # Relationship to author
    author = relationship("AuthorModel", back_populates="books", lazy="raise")
    
    @require_loaded("author")
    def get_author_name(self):
        """Method that requires author to be loaded."""
        return self.author.name


class TestRequireLoadedIntegration:
    """Integration tests for the require_loaded decorator using real database operations."""

    @pytest.fixture(scope="function")
    def session(self):
        """Create an in-memory SQLite session for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create tables
        ModelBase.metadata.create_all(bind=engine)
        
        yield session
        
        session.close()

    @pytest.fixture(autouse=True)
    def setup_test_data(self, session):
        """Set up test data for each test."""
        # Create test author
        self.author = AuthorModel(id=str(uuid.uuid4()), name="Test Author")
        session.add(self.author)
        
        # Create test books
        self.book1 = BookModel(
            id=str(uuid.uuid4()),
            title="Book One", 
            page_count=200,
            author_id=self.author.id
        )
        self.book2 = BookModel(
            id=str(uuid.uuid4()),
            title="Book Two", 
            page_count=150,
            author_id=self.author.id
        )
        session.add(self.book1)
        session.add(self.book2)
        session.commit()
        
        # Store IDs before expunging
        self.author_id = self.author.id
        self.book1_id = self.book1.id
        self.book2_id = self.book2.id
        
        # Clear session to ensure fresh loads
        session.expunge_all()

    def test_require_loaded_succeeds_with_preloaded_relationship(self, session):
        """Test that decorator succeeds when relationship is preloaded."""
        # Load author with books preloaded
        author = (
            session.query(AuthorModel)
            .options(selectinload(AuthorModel.books))
            .filter_by(id=self.author_id)
            .first()
        )
        
        # Should work because books are preloaded
        book_count = author.get_book_count()
        assert book_count == 2
        
        book_titles = author.get_book_titles()
        assert "Book One" in book_titles
        assert "Book Two" in book_titles

    def test_require_loaded_fails_without_preloaded_relationship(self, session):
        """Test that decorator fails when relationship is not preloaded."""
        # Load author WITHOUT preloading books
        author = session.query(AuthorModel).filter_by(id=self.author_id).first()
        
        # Should fail because books are not preloaded (lazy="raise" by default)
        with pytest.raises(RuntimeError, match="relationship 'books' not loaded for AuthorModel"):
            author.get_book_count()

    def test_require_loaded_with_joinedload_succeeds(self, session):
        """Test that decorator succeeds with joinedload."""
        # Load author with books using joinedload
        author = (
            session.query(AuthorModel)
            .options(joinedload(AuthorModel.books))
            .filter_by(id=self.author_id)
            .first()
        )
        
        # Should work because books are loaded
        book_count = author.get_book_count()
        assert book_count == 2

    def test_require_loaded_reverse_relationship(self, session):
        """Test decorator on reverse relationship (book -> author)."""
        # Load book with author preloaded
        book = (
            session.query(BookModel)
            .options(selectinload(BookModel.author))
            .filter_by(id=self.book1_id)
            .first()
        )
        
        # Should work because author is preloaded
        author_name = book.get_author_name()
        assert author_name == "Test Author"

    def test_require_loaded_reverse_relationship_fails_without_preload(self, session):
        """Test decorator fails on reverse relationship without preload."""
        # Load book WITHOUT preloading author
        book = session.query(BookModel).filter_by(id=self.book1_id).first()
        
        # Should fail because author is not preloaded
        with pytest.raises(RuntimeError, match="relationship 'author' not loaded for BookModel"):
            book.get_author_name()

    def test_require_loaded_with_multiple_fields(self, session):
        """Test decorator with multiple required fields."""
        # Test the decorator with multiple fields on existing model
        @require_loaded("books")
        def get_detailed_info(self):
            # This method requires books to be loaded
            return f"Author {self.name} has {len(self.books)} books"
        
        # Monkey patch the method onto AuthorModel for this test
        AuthorModel.get_detailed_info = get_detailed_info
        
        # Load author with books preloaded
        author = (
            session.query(AuthorModel)
            .options(selectinload(AuthorModel.books))
            .filter_by(id=self.author_id)
            .first()
        )
        
        # Should work because books relationship is loaded
        info = author.get_detailed_info()
        assert "Author Test Author has 2 books" == info
        
        # Clean up the monkey patch
        delattr(AuthorModel, 'get_detailed_info')

    def test_require_loaded_handles_empty_relationships(self, session):
        """Test decorator handles empty but loaded relationships correctly."""
        # Create author with no books
        author_no_books = AuthorModel(id=str(uuid.uuid4()), name="Author No Books")
        session.add(author_no_books)
        session.commit()
        
        # Store ID before expunging
        author_no_books_id = author_no_books.id
        session.expunge_all()
        
        # Load with books preloaded (but empty)
        author = (
            session.query(AuthorModel)
            .options(selectinload(AuthorModel.books))
            .filter_by(id=author_no_books_id)
            .first()
        )
        
        # Should work even with empty relationship
        book_count = author.get_book_count()
        assert book_count == 0
        
        book_titles = author.get_book_titles()
        assert book_titles == []

    def test_require_loaded_preserves_method_signature(self, session):
        """Test that decorator preserves original method signature and behavior."""
        # Load author with books preloaded
        author = (
            session.query(AuthorModel)
            .options(selectinload(AuthorModel.books))
            .filter_by(id=self.author_id)
            .first()
        )
        
        # Verify the decorated method works correctly
        assert callable(author.get_book_count)
        assert author.get_book_count.__name__ == "get_book_count"
        
        # Verify it returns the expected type and value
        count = author.get_book_count()
        assert isinstance(count, int)
        assert count == 2