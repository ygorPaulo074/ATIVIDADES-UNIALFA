-- Saldo atual da carteira: saldo inicial + Σ transações efetivadas
CREATE OR REPLACE FUNCTION wallet_balance(p_wallet_id BIGINT) RETURNS NUMERIC AS $$
DECLARE base NUMERIC; mov NUMERIC;
BEGIN
  SELECT initial_balance INTO base FROM wallets WHERE id = p_wallet_id;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT COALESCE(SUM(CASE WHEN type = 'inflow' THEN amount ELSE -amount END), 0)
    INTO mov FROM transactions WHERE wallet_id = p_wallet_id AND status = 'settled';

  RETURN base + mov;
END;
$$ LANGUAGE plpgsql STABLE;
