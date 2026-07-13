-- Add answer_type and quiz_options columns to tasks table
ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS answer_type TEXT NOT NULL DEFAULT 'link',
ADD COLUMN IF NOT EXISTS quiz_options JSONB NOT NULL DEFAULT '[]',
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_tasks_answer_type ON public.tasks(answer_type);
CREATE INDEX IF NOT EXISTS idx_tasks_is_active ON public.tasks(is_active);
