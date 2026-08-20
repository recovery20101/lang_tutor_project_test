export interface GrammarRule {
  id: string;
  title: string;
  content: string; // Markdown текст правила
  level: 'A1' | 'A2' | 'B1' | 'B2';
  source_section: string;
  explanation?: string;
}

export interface CheckResponse {
  is_correct: boolean;
  feedback: string;
  correct_answer?: string;
}