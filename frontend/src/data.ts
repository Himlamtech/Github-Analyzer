import { EcosystemCategory } from './types';

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
