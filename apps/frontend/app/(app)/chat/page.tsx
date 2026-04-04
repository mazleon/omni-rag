'use client';

import { ChatInterface } from '@/components/chat/ChatInterface';

export default function ChatPage() {
  return (
    <div className="flex h-full">
      <div className="mx-auto flex w-full max-w-4xl flex-col">
        <ChatInterface />
      </div>
    </div>
  );
}
