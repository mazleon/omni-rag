import { redirect } from "next/navigation";

export default function Home() {
  // Directly forward to the chat interface as the primary landing feature
  redirect("/chat");
}
