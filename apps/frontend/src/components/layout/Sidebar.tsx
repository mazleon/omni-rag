import Link from "next/link";
import { FolderGit2, MessagesSquare, Settings } from "lucide-react";
import { Button } from "../ui/button";

export function Sidebar() {
  return (
    <aside className="w-64 border-r bg-card glass flex flex-col h-screen fixed left-0 top-0 z-40 hidden md:flex transition-all duration-300">
      <div className="p-6 border-b flex items-center gap-3">
        <div className="bg-brand text-brand-foreground p-2 rounded-lg">
          <FolderGit2 className="size-5" />
        </div>
        <h1 className="font-bold text-lg tracking-tight">OmniRAG</h1>
      </div>
      <nav className="p-4 flex-1 space-y-2">
        <Link href="/chat">
          <Button variant="ghost" className="w-full justify-start gap-3 opacity-80 hover:opacity-100">
            <MessagesSquare className="size-4" />
            Chat
          </Button>
        </Link>
        <Link href="/documents">
          <Button variant="ghost" className="w-full justify-start gap-3 opacity-80 hover:opacity-100">
            <FolderGit2 className="size-4" />
            Documents
          </Button>
        </Link>
      </nav>
      <div className="p-4 border-t">
        <Button variant="ghost" className="w-full justify-start gap-3 text-muted-foreground outline-none ring-0">
          <Settings className="size-4" />
          Settings
        </Button>
      </div>
    </aside>
  );
}
