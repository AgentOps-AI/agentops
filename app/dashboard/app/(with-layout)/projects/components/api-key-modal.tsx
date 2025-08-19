import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { BackgroundImageOverlay } from '@/components/ui/background-image-overlay';
import { Tables } from '@/lib/types_db';

interface ApiKeyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Tables<'projects'>;
}

export function ApiKeyModal({ open, onOpenChange, project }: ApiKeyModalProps) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent
        className="w-3/4 rounded-2xl border border-white bg-[#F7F8FF] sm:w-[500px] sm:rounded-2xl"
        overlayClassName="bg-white/40 backdrop-blur-md"
      >
        <BackgroundImageOverlay />
        <div className="relative">
          <DialogHeader className="mb-7">
            <DialogTitle className="text-left text-2xl font-medium text-primary">Great</DialogTitle>
            <DialogDescription className="text-left font-medium text-secondary dark:text-white">
              Here is your API key. Copy the key and add it to your code{' '}
              <span className="font-semibold text-primary underline">Learn more</span>
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg bg-white p-4">
            <code className="text-sm">{project.api_key}</code>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
