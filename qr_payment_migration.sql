-- PAYMENT CONFIG (QR code settings, single-row config)
CREATE TABLE IF NOT EXISTS public.payment_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    qr_image_url TEXT,
    qr_public_id TEXT,
    upi_id TEXT,
    amount INT DEFAULT 9,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add transaction_id to profiles (for QR payment tracking)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS transaction_id TEXT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_profiles_transaction_id ON public.profiles(transaction_id);

ALTER TABLE public.payment_config ENABLE ROW LEVEL SECURITY;

-- Insert default config row
INSERT INTO public.payment_config (qr_image_url, upi_id, amount)
VALUES (NULL, NULL, 9)
ON CONFLICT DO NOTHING;
