-- PLATFORM SETTINGS (single-row global config)
CREATE TABLE IF NOT EXISTS public.platform_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tasks_visible BOOLEAN DEFAULT true,
    certificate_download_enabled BOOLEAN DEFAULT false,
    active_module TEXT DEFAULT 'Module 1' CHECK (active_module IN ('Module 1', 'Module 2')),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES public.admin_users(id) ON DELETE SET NULL
);

ALTER TABLE public.platform_settings ENABLE ROW LEVEL SECURITY;

-- Insert default row
INSERT INTO public.platform_settings (tasks_visible, certificate_download_enabled, active_module)
VALUES (true, false, 'Module 1')
ON CONFLICT DO NOTHING;
