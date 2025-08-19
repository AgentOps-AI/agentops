import { ProjectsPageContent } from './components/page-content';

export default async function ProjectsPage() {
  return (
    <>
      <div className="flex max-w-6xl flex-col gap-2 p-2">
        <ProjectsPageContent />
      </div>
    </>
  );
}
