-- Trigger: limite de 5 tags por usuário
CREATE OR REPLACE FUNCTION trg_tags_limit() RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT COUNT(*) FROM tags WHERE user_id = NEW.user_id) >= 5 THEN
    RAISE EXCEPTION 'Limite de 5 tags por usuário atingido';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tags_limit BEFORE INSERT ON tags
  FOR EACH ROW EXECUTE FUNCTION trg_tags_limit();
