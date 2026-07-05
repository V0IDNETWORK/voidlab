export interface Category {
  id: number;
  code: string;
  name: string;
  short_name: string;
  description: string;
  icon: string;
  order: number;
  lab_count: number;
}

export type Difficulty = "easy" | "medium" | "hard" | "insane";

export interface LabSummary {
  id: number;
  title: string;
  slug: string;
  category: Category;
  difficulty: Difficulty;
  summary: string;
  points: number;
  estimated_minutes: number;
  is_completed: boolean;
}

export interface Hint {
  id: number;
  order: number;
  point_penalty: number;
  is_unlocked: boolean;
  text: string | null;
}

export interface LabDetail extends LabSummary {
  briefing: string;
  objective: string;
  target_url: string | null;
  hints: Hint[];
  attempts: number;
  has_solution: boolean;
}

export interface Submission {
  id: number;
  lab: number;
  is_correct: boolean;
  points_awarded: number;
  created_at: string;
}

export interface Profile {
  id: number;
  username: string;
  email: string;
  display_name: string;
  bio: string;
  role: string;
  total_points: number;
  labs_completed: number;
  is_admin_operator: boolean;
  date_joined: string;
}

export interface LeaderboardRow {
  id: number;
  username: string;
  display_name: string;
  total_points: number;
  labs_completed: number;
}
