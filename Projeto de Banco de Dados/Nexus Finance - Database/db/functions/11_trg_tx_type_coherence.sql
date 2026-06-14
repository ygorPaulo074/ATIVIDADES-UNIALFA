-- Trigger: coerência tipo da transação x tipo da categoria
CREATE OR REPLACE FUNCTION trg_tx_type_coherence() RETURNS TRIGGER AS $$
DECLARE cat_type category_type;
BEGIN
  IF NEW.category_id IS NULL THEN RETURN NEW; END IF;
  SELECT type INTO cat_type FROM categories WHERE id = NEW.category_id;
  IF (NEW.type = 'inflow'  AND cat_type <> 'income')
  OR (NEW.type = 'outflow' AND cat_type <> 'expense') THEN
    RAISE EXCEPTION 'Categoria (%) incompatível com transação %', cat_type, NEW.type;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tx_type_coherence BEFORE INSERT OR UPDATE ON transactions
  FOR EACH ROW EXECUTE FUNCTION trg_tx_type_coherence();
