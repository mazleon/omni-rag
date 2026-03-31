import { Document } from "@/lib/types";
import { Copy, FileLock2, MoreVertical } from "lucide-react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

const STYLES_BY_STATUS = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-900/50",
  processing: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-900/50",
  indexed: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-900/50",
  error: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-900/50",
};

export function DocumentCard({ doc }: { doc: Document }) {
  const dt = new Date(doc.created_at);
  const sizeMb = doc.file_size_bytes ? (doc.file_size_bytes / 1024 / 1024).toFixed(2) + " MB" : "Unknown";

  return (
    <div className="group relative flex items-center justify-between p-4 bg-card outline outline-1 outline-transparent border border-border/50 hover:outline-brand/20 shadow-sm hover:shadow-md transition-all rounded-xl glass">
      <div className="flex items-center gap-4 flex-1 overflow-hidden">
        <div className="p-2.5 bg-muted rounded-lg text-muted-foreground group-hover:bg-brand/10 group-hover:text-brand transition-colors">
          <FileLock2 className="size-5" />
        </div>
        <div className="flex flex-col flex-1 overflow-hidden">
          <span className="font-semibold text-sm tracking-tight text-foreground truncate">{doc.filename}</span>
          <div className="flex items-center gap-2 mt-1 -ml-0.5">
            <span className="text-xs text-muted-foreground font-mono">{sizeMb}</span>
            <span className="text-xs text-muted-foreground/30">•</span>
            <span className="text-xs text-muted-foreground tabular-nums">
              {dt.toLocaleDateString()} {dt.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0 ml-4">
        <Badge variant="outline" className={`capitalize shadow-none ${STYLES_BY_STATUS[doc.status]}`}>
          {doc.status}
        </Badge>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          <MoreVertical className="size-4" />
        </Button>
      </div>
    </div>
  );
}
