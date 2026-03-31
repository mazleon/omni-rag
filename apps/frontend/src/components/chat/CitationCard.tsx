import { Citation } from "@/lib/types";
import { Card, CardContent, CardHeader } from "../ui/card";
import { Badge } from "../ui/badge";
import { FileText } from "lucide-react";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  return (
    <Card className="cursor-pointer hover:ring-2 hover:ring-brand/50 transition-all bg-card/60 backdrop-blur-sm shadow-sm hover:shadow-md border-border/50 group">
      <CardHeader className="py-2.5 px-3 flex flex-row items-center justify-between gap-2 bg-muted/20 border-b border-border/30">
        <div className="flex items-center gap-2 overflow-hidden flex-1">
          <Badge variant="outline" className="bg-background text-xs font-mono px-1.5 py-0 shadow-sm border-brand/20 group-hover:border-brand/40 transition-colors">[{index + 1}]</Badge>
          <FileText className="size-3.5 text-brand opacity-80" />
          <span className="text-xs font-medium text-foreground truncate flex-1">
            {citation.document_title}
          </span>
        </div>
        {citation.page_number && (
          <Badge variant="secondary" className="text-[10px] uppercase font-mono tracking-wider opacity-80 bg-brand/5 text-brand/80">p.{citation.page_number}</Badge>
        )}
      </CardHeader>
      <CardContent className="py-3 px-3">
        <p className="text-xs text-muted-foreground line-clamp-4 leading-relaxed tracking-wide">
          <span className="text-brand/50 mr-1 italic">"</span>
          {citation.excerpt}
          <span className="text-brand/50 ml-1 italic">"</span>
        </p>
      </CardContent>
    </Card>
  );
}
