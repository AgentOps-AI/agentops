import React from 'react';

export interface RepoDropdownProps {
  orgsWithRepos: Array<{ org: string; repos: any[] }>;
  onSelect: (repo: any) => void;
  isOpen: boolean;
  onClose: () => void;
}

const RepoDropdown: React.FC<RepoDropdownProps> = ({ orgsWithRepos, onSelect, isOpen, onClose }) => {
  const [filter, setFilter] = React.useState('');
  const filteredOrgsWithRepos = React.useMemo(() => {
    if (!filter.trim()) {
      // Sort repos for each org alphabetically by repo name
      return orgsWithRepos.map(org => ({
        ...org,
        repos: [...org.repos].sort((a, b) => {
          const aName = ((a.full_name || '').split('/')[1] || a.full_name || a.name || '').toLowerCase();
          const bName = ((b.full_name || '').split('/')[1] || b.full_name || b.name || '').toLowerCase();
          return aName.localeCompare(bName);
        })
      }));
    }
    const filterWords = filter.toLowerCase().split(/\s+/).filter(Boolean);
    return orgsWithRepos.map(org => {
      // Sort repos before filtering
      const sortedRepos = [...org.repos].sort((a, b) => {
        const aName = ((a.full_name || '').split('/')[1] || a.full_name || a.name || '').toLowerCase();
        const bName = ((b.full_name || '').split('/')[1] || b.full_name || b.name || '').toLowerCase();
        return aName.localeCompare(bName);
      });
      return {
        ...org,
        repos: sortedRepos.filter(repo => {
          const repoName = (repo.full_name || '').split('/')[1] || repo.full_name || repo.name || '';
          const orgName = org.org || '';
          const fullName = (repo.full_name || '') + ' ' + orgName;
          const target = [repoName, orgName, fullName].join(' ').toLowerCase();
          // All filter words must be present somewhere in the target string
          return filterWords.every(word => target.includes(word));
        })
      };
    }).filter(org => org.repos.length > 0);
  }, [orgsWithRepos, filter]);

  if (!isOpen) return null;

  const clearFilter = () => {
    setFilter('');
  };

  return (
    <div className="absolute z-20 mt-2 w-96 max-h-80 bg-white border border-[rgba(222,224,244,1)] rounded shadow-lg">
      {/* Filter input */}
      <div className="p-3 border-b border-[rgba(222,224,244,1)]">
        <div className="relative">
          <input
            type="text"
            placeholder="Filter repositories..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full px-3 py-2 pr-8 text-[14px] border border-[rgba(222,224,244,1)] rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
          {filter && (
            <button
              onClick={clearFilter}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(230,90,126,1)] transition-colors"
              title="Clear filter"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1 1L11 11M1 11L11 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          )}
        </div>
      </div>
      {/* Scrollable repo list */}
      <div className="max-h-64 overflow-y-auto p-2">
        {filteredOrgsWithRepos.length === 0 && (
          <div className="text-[14px] text-[rgba(230,90,126,1)]">
            {filter ? 'No repositories match your filter.' : 'No repositories found.'}
          </div>
        )}
        {filteredOrgsWithRepos.map((org) => (
          <div key={org.org} className="mb-2">
            <div className="font-semibold text-[15px] text-[rgba(20,27,52,1)] mb-1">{org.org}</div>
            {org.repos.map((repo) => {
              const repoName = (repo.full_name || '').split('/')[1] || repo.full_name || repo.name;
              return (
                <div
                  key={repo.id || repo.full_name}
                  className="ml-4 p-2 flex items-center gap-2 cursor-pointer hover:bg-[rgba(222,224,244,0.5)] rounded text-[14px]"
                  onClick={() => { onSelect(repo); onClose(); }}
                >
                  {/* GitHub logo SVG */}
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0"><path fillRule="evenodd" clipRule="evenodd" d="M8 1.333c-3.682 0-6.667 2.985-6.667 6.667 0 2.946 1.91 5.444 4.557 6.333.333.06.456-.144.456-.32 0-.158-.006-.577-.009-1.133-1.855.403-2.247-.894-2.247-.894-.303-.77-.74-.975-.74-.975-.605-.414.046-.406.046-.406.67.047 1.022.688 1.022.688.595 1.02 1.56.726 1.94.555.06-.431.233-.726.424-.893-1.482-.168-3.04-.741-3.04-3.297 0-.728.26-1.323.687-1.79-.069-.168-.298-.846.065-1.764 0 0 .56-.18 1.833.684a6.37 6.37 0 0 1 1.667-.224c.566.003 1.137.077 1.667.224 1.272-.864 1.832-.684 1.832-.684.364.918.135 1.596.066 1.764.428.467.686 1.062.686 1.79 0 2.56-1.56 3.127-3.048 3.292.24.207.454.617.454 1.244 0 .898-.008 1.623-.008 1.844 0 .178.12.384.46.319C12.76 13.444 14.667 10.946 14.667 8c0-3.682-2.985-6.667-6.667-6.667Z" fill="#181717"/></svg>
                  {repoName}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default RepoDropdown; 