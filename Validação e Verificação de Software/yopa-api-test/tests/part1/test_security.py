"""
Parte 1 — Módulo: src/infrastructure/security.py

ESCOPO
------
Funções puras de segurança: geração e hash de API key, verificação segura,
e criptografia simétrica de segredos (Fernet) para SQL connection strings
e credenciais de IA por agente.

NATUREZA
--------
Código determinístico sem I/O — perfeito para testes unitários puros.

TIPOS DE TESTE
--------------
- unit         : todas as funções
- regression   : verify_api_key usa hmac.compare_digest (comparação de tempo
                 constante contra ataques de timing)
"""
import pytest

from tests.shared.log_helper import logged

from src.infrastructure.security import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    encrypt_secret,
    decrypt_secret,
    mask_connection_string,
)


@pytest.mark.unit
@pytest.mark.part1
class TestHashApiKey:
    """Validar geração de hash SHA-256 a partir da api_key."""

    @logged
    def test_hash_is_deterministic(self):
        """hash_api_key(x) sempre retorna o mesmo digest para o mesmo input."""
        assert hash_api_key("abc123") == hash_api_key("abc123")

    @logged
    def test_hash_differs_for_different_inputs(self):
        """Inputs distintos devem produzir hashes distintos."""
        assert hash_api_key("abc") != hash_api_key("abd")

    @logged
    def test_hash_returns_64_char_hex_string(self):
        """SHA-256 sempre produz 64 caracteres hex."""
        digest = hash_api_key("qualquer-coisa")
        assert isinstance(digest, str)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


@pytest.mark.unit
@pytest.mark.part1
class TestVerifyApiKey:
    """Validar verificação de api_key contra hash armazenado."""

    @logged
    def test_correct_secret_verifies(self):
        """verify_api_key(secret, hash(secret)) deve retornar True."""
        secret = "minha-chave-real"
        stored = hash_api_key(secret)
        assert verify_api_key(secret, stored) is True

    @logged
    def test_wrong_secret_fails(self):
        """Segredo errado deve retornar False (não levantar)."""
        stored = hash_api_key("certo")
        assert verify_api_key("errado", stored) is False

    @logged
    def test_empty_secret_fails_against_real_hash(self):
        """String vazia não deve passar como secret válido."""
        stored = hash_api_key("certo")
        assert verify_api_key("", stored) is False


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.part1
class TestVerifyApiKeyTimingSafety:
    """
    Regressão de segurança: verify_api_key deve usar hmac.compare_digest
    (comparação de tempo constante). Comparação com `==` permite ataque
    de timing onde o atacante mede a duração para descobrir prefixos.

    Como não dá para medir o tempo aqui sem ruído, validamos
    indiretamente: a função retorna False sem exceção mesmo quando o
    hash armazenado tem tamanho diferente do esperado — sinal de que
    compare_digest está sendo usado (ele lida com tamanhos diferentes
    sem revelar info).
    """

    @logged
    def test_returns_false_for_mismatched_hash_length(self):
        assert verify_api_key("qualquer", "hash-curto") is False

    @logged
    def test_returns_false_for_empty_stored_hash(self):
        assert verify_api_key("qualquer", "") is False


@pytest.mark.unit
@pytest.mark.part1
class TestGenerateApiKey:
    """
    Validar a geração de secret URL-safe.

    Nota: generate_api_key() retorna APENAS o secret. O formato final
    `{agent_id}.{secret}` é montado fora desta função (no AgentService).
    """

    @logged
    def test_returns_non_empty_string(self):
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 0

    @logged
    def test_two_calls_produce_different_secrets(self):
        """secrets.token_urlsafe é aleatório criptográfico — nunca repete."""
        assert generate_api_key() != generate_api_key()

    @logged
    def test_only_url_safe_characters(self):
        """O secret deve conter apenas chars URL-safe (a-z, A-Z, 0-9, -, _)."""
        key = generate_api_key()
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert all(c in allowed for c in key)


@pytest.mark.unit
@pytest.mark.part1
class TestEncryptDecryptSecret:
    """
    Validar round-trip de criptografia simétrica (Fernet).
    Usado para armazenar SQL connection strings e ai_api_key por agente.
    """

    @logged
    def test_roundtrip_preserves_plaintext(self):
        """decrypt_secret(encrypt_secret(x)) == x"""
        plaintext = "postgresql://user:pass@localhost/db"
        cipher = encrypt_secret(plaintext)
        assert decrypt_secret(cipher) == plaintext

    @logged
    def test_encrypted_starts_with_enc_prefix(self):
        """encrypt_secret prefixa com 'enc:' para sinalizar criptografia."""
        cipher = encrypt_secret("segredo")
        assert cipher.startswith("enc:")

    @logged
    def test_encrypted_does_not_contain_plaintext(self):
        """O cipher não deve conter o plaintext em claro."""
        plaintext = "sqlite:///tmp/segredo.db"
        cipher = encrypt_secret(plaintext)
        assert plaintext not in cipher

    @logged
    def test_already_encrypted_is_returned_as_is(self):
        """Encriptar uma string já encriptada não deve duplicar o cipher."""
        cipher = encrypt_secret("segredo")
        again = encrypt_secret(cipher)
        assert again == cipher

    @logged
    def test_decrypt_plaintext_returns_as_is(self):
        """decrypt sobre string sem prefixo enc: devolve igual (idempotente)."""
        assert decrypt_secret("não-encriptado") == "não-encriptado"

    @logged
    def test_decrypt_with_invalid_cipher_raises(self):
        """Cipher inválido (com prefixo, mas corrompido) deve levantar ValueError."""
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_secret("enc:lixo-invalido-que-nao-e-fernet")


@pytest.mark.unit
@pytest.mark.part1
class TestMaskConnectionString:
    """Mascarar credenciais para logs (sem expor senha em texto claro)."""

    @logged
    def test_masks_password_in_postgres_url(self):
        masked = mask_connection_string("postgresql://admin:senha123@host/db")
        assert "senha123" not in masked
        assert "***" in masked

    @logged
    def test_returns_encrypted_marker_for_encrypted_input(self):
        cipher = encrypt_secret("postgresql://x:y@h/d")
        assert mask_connection_string(cipher) == "[encrypted]"

    @logged
    def test_returns_string_as_is_when_no_password(self):
        url = "sqlite:///tmp/local.db"
        assert mask_connection_string(url) == url
