-- PENDING REGISTRATIONS (short-lived, keyed by Razorpay order_id)
CREATE TABLE public.pending_registrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,
    form_data JSONB NOT NULL,
    amount INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 minutes'
);

CREATE INDEX idx_pending_registrations_order ON public.pending_registrations(order_id);

-- PAYMENTS (permanent record of completed payments)
CREATE TABLE public.payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    razorpay_order_id TEXT UNIQUE NOT NULL,
    razorpay_payment_id TEXT,
    razorpay_signature TEXT,
    amount INT NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'captured', 'failed', 'refunded')),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    captured_at TIMESTAMPTZ
);

CREATE INDEX idx_payments_user ON public.payments(user_id);
CREATE INDEX idx_payments_order ON public.payments(razorpay_order_id);

ALTER TABLE public.pending_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
