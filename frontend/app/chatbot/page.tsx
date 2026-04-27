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
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Chatbot</div>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                Ask GitHub data in plain language
              </h1>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Query live trend data, repo briefs, topic rotation, and category movement
              through a chat interface that stays grounded in the existing APIs.
            </p>
          </div>

          <GitHubDataChatbot />
        </section>
      </main>

      <Footer />
    </div>
  );
}
