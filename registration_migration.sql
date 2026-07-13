CREATE TABLE IF NOT EXISTS domains (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO domains (name) VALUES
    ('Web Development'),
    ('AI/ML'),
    ('Mobile App Development'),
    ('Blockchain'),
    ('Cybersecurity'),
    ('Cloud Computing'),
    ('IoT'),
    ('AR/VR')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS registrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('solo', 'team')),
    email TEXT,
    team_name TEXT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    college TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    domain TEXT NOT NULL,
    transaction_id TEXT UNIQUE NOT NULL,
    amount INT NOT NULL,
    member_count INT NOT NULL DEFAULT 1,
    team_members JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_registrations_email ON registrations(email);
CREATE INDEX IF NOT EXISTS idx_registrations_team_name ON registrations(team_name);
CREATE INDEX IF NOT EXISTS idx_registrations_type ON registrations(type);
