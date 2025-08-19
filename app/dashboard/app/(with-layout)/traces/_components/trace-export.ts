import { ITrace } from '@/types/ITrace';
import { ISpan } from '@/types/ISpan';
import { toast } from '@/components/ui/use-toast';

// Helper function to download trace data as JSON
export const downloadTraceAsJson = async (
  traceId: string,
  trace: ITrace | null,
  spans: ISpan[],
) => {
  try {
    // Export raw data as-is
    const exportData = {
      trace: trace,
      spans: spans,
    };

    // Convert to JSON string with pretty formatting
    const jsonString = JSON.stringify(exportData, null, 2);

    // Create filename
    const date = new Date();
    const dateStr = date.toISOString().split('T')[0];
    const timeStr = date.toTimeString().split(' ')[0].replace(/:/g, '-');
    const shortTraceId = traceId.substring(0, 8);
    const filename = `trace_${shortTraceId}_${dateStr}_${timeStr}.json`;

    // Try File System Access API first (shows native save dialog)
    if ('showSaveFilePicker' in window) {
      try {
        const handle = await (window as any).showSaveFilePicker({
          suggestedName: filename,
          types: [
            {
              description: 'JSON Files',
              accept: { 'application/json': ['.json'] },
            },
          ],
        });
        const writable = await handle.createWritable();
        await writable.write(jsonString);
        await writable.close();

        toast({
          title: 'Trace exported successfully',
          description: `Saved ${spans.length} spans as JSON`,
        });
        return;
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.warn('File System Access API failed, falling back to download link');
        } else {
          return; // User cancelled
        }
      }
    }

    // Fallback: Use traditional download approach
    // Note: Direct DOM manipulation is standard for file downloads even in React
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonString);
    const link = document.createElement('a');
    link.href = dataUri;
    link.download = filename;

    // Trigger download without adding to DOM (modern browsers support this)
    link.click();

    toast({
      title: 'Trace exported',
      description: `Downloaded ${spans.length} spans as JSON. If blocked by macOS, right-click the file and select "Open".`,
    });
  } catch (error) {
    console.error('Error exporting trace:', error);
    toast({
      title: 'Export failed',
      description: 'Could not export trace data. Please try again.',
      variant: 'destructive',
    });
  }
};

// Helper function to copy trace data to clipboard
export const copyTraceJsonToClipboard = async (trace: ITrace | null, spans: ISpan[]) => {
  try {
    const exportData = {
      trace: trace,
      spans: spans,
    };

    const jsonString = JSON.stringify(exportData, null, 2);
    await navigator.clipboard.writeText(jsonString);

    toast({
      title: 'Copied to clipboard',
      description: `${spans.length} spans copied as JSON. You can paste this into any text editor.`,
    });
  } catch (error) {
    console.error('Error copying to clipboard:', error);
    toast({
      title: 'Copy failed',
      description: 'Could not copy to clipboard. Please try the download option instead.',
      variant: 'destructive',
    });
  }
};
