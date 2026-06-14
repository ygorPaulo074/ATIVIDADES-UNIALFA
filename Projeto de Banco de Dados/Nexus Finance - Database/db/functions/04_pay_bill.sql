-- Quita (total ou parcial) uma conta criando a transação correspondente
CREATE OR REPLACE FUNCTION pay_bill(
  p_bill_id BIGINT, p_wallet_id BIGINT, p_amount NUMERIC, p_date DATE DEFAULT CURRENT_DATE
) RETURNS BIGINT AS $$
DECLARE b bills%ROWTYPE; tx_type transaction_type; new_id BIGINT;
BEGIN
  SELECT * INTO b FROM bills WHERE id = p_bill_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'bill % não encontrada', p_bill_id; END IF;
  IF b.cancelled_at IS NOT NULL THEN RAISE EXCEPTION 'bill % está cancelada', p_bill_id; END IF;

  -- receivable gera entrada (inflow); payable gera saída (outflow)
  tx_type := CASE b.type WHEN 'receivable' THEN 'inflow' ELSE 'outflow' END;

  INSERT INTO transactions(
    user_id, wallet_id, type, description, amount, date,
    category_id, payment_method_id, bill_id, status
  ) VALUES (
    b.user_id, p_wallet_id, tx_type, b.description, p_amount, p_date,
    b.category_id, b.payment_method_id, p_bill_id, 'settled'
  ) RETURNING id INTO new_id;

  RETURN new_id;
END;
$$ LANGUAGE plpgsql;
