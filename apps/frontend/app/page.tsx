import { redirect } from 'next/navigation';

// Root redirects to chat (auth guard in (app)/layout.tsx handles unauthenticated users)
export default function RootPage() {
  redirect('/chat');
}
