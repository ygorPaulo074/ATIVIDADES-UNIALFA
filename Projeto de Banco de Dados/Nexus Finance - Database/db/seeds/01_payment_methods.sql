-- ===== SEED: formas de pagamento (lista fixa) =====
INSERT INTO payment_methods (name) VALUES
  ('PIX'),
  ('Dinheiro'),
  ('Cartão de Débito'),
  ('Cartão de Crédito'),
  ('Boleto'),
  ('Transferência (TED/DOC)'),
  ('Outros')
ON CONFLICT (name) DO NOTHING;
