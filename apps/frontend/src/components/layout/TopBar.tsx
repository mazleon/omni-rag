import { BellRing, Search } from "lucide-react";
import { Input } from "../ui/input";
import { Button } from "../ui/button";

export function TopBar() {
  return (
    <header className="h-16 border-b bg-background/50 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center gap-4 max-w-sm w-full">
        <div className="relative w-full">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search across collections..." 
            className="pl-9 bg-muted/40 border-none w-full" 
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
          <BellRing className="size-5" />
        </Button>
        <div className="h-8 w-8 rounded-full bg-brand/20 border border-brand/40" />
      </div>
    </header>
  );
}
