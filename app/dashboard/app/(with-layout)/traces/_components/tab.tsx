import { cn } from '@/lib/utils';

interface TabProps {
    label: string;
    isActive: boolean;
    onClick: () => void;
}

const Tab = ({ label, isActive, onClick }: TabProps) => {
    return (
        <button
            className={cn(
                'relative px-4 py-1.5 font-medium',
                isActive ? 'text-primary' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300',
            )}
            onClick={onClick}
        >
            {label}
            {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-black dark:bg-white/80 shadow-[0_1px_3px_rgba(0,0,0,0.3)] dark:shadow-[0_1px_3px_rgba(255,255,255,0.2)]"></div>
            )}
        </button>
    );
};

export default Tab;