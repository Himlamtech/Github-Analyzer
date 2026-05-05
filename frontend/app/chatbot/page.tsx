"use client";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { GitHubDataChatbot } from "@/components/ai/GitHubDataChatbot";

export default function ChatbotPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl px-4 pb-10 sm:px-6">
        <section className="space-y-4 py-2">
          <GitHubDataChatbot />
        </section>
      </main>

      <Footer />
    </div>
  );
}
