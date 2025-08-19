import { TextSectionProps } from '../types';

export const TextSection = ({ title, content }: TextSectionProps) => {
    return (
        <div className="rounded-md border p-3" style={{ borderColor: 'rgba(222, 224, 244, 1)' }}>
            <span className="font-bold">{title}</span>
            <p className="mt-2 whitespace-pre-wrap text-sm text-[rgba(20,27,52,0.74)] dark:text-[rgba(225,226,242,0.74)]">
                {content}
            </p>
        </div>
    );
}; 