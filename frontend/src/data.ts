import { EcosystemCategory, NewsImpactEvent } from './types';

export const ECOSYSTEM_CATEGORIES: EcosystemCategory[] = [
  {
    id: 'cat-1',
    title: 'Coding Agents & Automation',
    score: 9.4,
    growth: '+145% MoM',
    momentum: 88,
    description: 'Replacing simple tab-completions with self-compiling multi-turn execution agents.'
  },
  {
    id: 'cat-2',
    title: 'Multimodal Interfaces',
    score: 7.8,
    growth: '+82% MoM',
    momentum: 68,
    description: 'WebRTC ultra-low-latency real-time voice pipes and contextual audio-visual tokens.'
  },
  {
    id: 'cat-3',
    title: 'Safety & Guardrails',
    score: 6.2,
    growth: '+14% MoM',
    momentum: 40,
    description: 'Edge-based compliance filters and real-time policy checks before generation completes.'
  }
];

export const NEWS_IMPACT_EVENTS: NewsImpactEvent[] = [
  {
    id: 'news-1',
    date: 'Oct 22, 2024',
    timeOffset: '12 Hours After',
    headline: 'Anthropic Launches Computer-Use API in Upgrade of Claude 3.5 Sonnet',
    category: 'System Automation',
    summary: 'Anthropic unveiled features enabling Claude models to control keyboard strokes, mice cursors, and visual screen buffers directly.',
    causalityScore: 92,
    codeImpactMetric: '+340% System-level Python Packages',
    narrativeText: 'Developers rapidly transitioned from prompt-engineered API endpoints to writing custom OS-level wrappers. Within 12 hours of the announcement, secondary repositories tracking active browser automations and OS automation forks surged exponentially.',
    codeTrendData: [
      { time: '0h', value: 12 },
      { time: '2h', value: 18 },
      { time: '6h', value: 45 },
      { time: '12h', value: 140 },
      { time: '24h', value: 280 },
      { time: '48h', value: 340 }
    ]
  },
  {
    id: 'news-2',
    date: 'Sep 12, 2024',
    timeOffset: '3 Hours After',
    headline: 'OpenAI Releases o1 Series with Multi-Turn Reasoning Capabilities',
    category: 'Reasoning Frameworks',
    summary: 'Launches o1-preview and o1-mini engines incorporating reinforcement learning to compute dynamic chain-of-thought steps before answering.',
    causalityScore: 88,
    codeImpactMetric: '-45% Prompt-Hacks; +160% Agent Loops',
    narrativeText: 'The introduction of model-level reasoning shifted engineering focus away from brittle prompt optimization. Standard "chain of thought prompting" repositories experienced an immediate cliff in contribution activity. Concurrently, orchestration frameworks implementing complex logic checking saw a breakout velocity of $+160\\%$ as latent tokens became a budget priority.',
    codeTrendData: [
      { time: '0h', value: 95 },
      { time: '4h', value: 75 },
      { time: '12h', value: 50 },
      { time: '24h', value: 120 },
      { time: '48h', value: 180 },
      { time: '72h', value: 240 }
    ]
  },
  {
    id: 'news-3',
    date: 'Aug 05, 2024',
    timeOffset: '24 Hours After',
    headline: 'The Multi-Modal Native Era: Gemini 1.5 Pro Native Audio Understanding',
    category: 'Speech & Acoustic Layers',
    summary: 'Integration of raw, token-level audio input bypasses Whisper speech-to-text filters to extract contextual pitch, tone, and inflection directly.',
    causalityScore: 85,
    codeImpactMetric: '+180% WebRTC Pipe Forks',
    narrativeText: 'Native acoustic inputs made speech-to-text layers redundant overnight. Active repository fork records indicate developers redirected engineering capital to low-level pipelines such as Opus audio packets and direct multi-stream WebRTC interfaces to support continuous model interactions.',
    codeTrendData: [
      { time: '0h', value: 50 },
      { time: '4h', value: 62 },
      { time: '8h', value: 90 },
      { time: '12h', value: 110 },
      { time: '24h', value: 165 },
      { time: '48h', value: 180 }
    ]
  }
];
