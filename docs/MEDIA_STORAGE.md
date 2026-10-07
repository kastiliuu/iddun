# Arquitetura de mídia do IDDUN

## Contrato persistido

O domínio salva referências de mídia como chaves relativas:

```text
uploads/<categoria>/<arquivo>
```

Esse contrato é independente do backend físico.

## Backends

### local

Uso principal:

- desenvolvimento local;
- preview temporário;
- testes.

Configuração:

```text
MEDIA_STORAGE_BACKEND=local
UPLOAD_FOLDER=/caminho/para/uploads
```

O filesystem do Render Free não deve ser tratado como persistente.

### s3

Backend genérico compatível com API S3.

Configuração:

```text
MEDIA_STORAGE_BACKEND=s3
MEDIA_S3_BUCKET=...
MEDIA_S3_REGION=...
MEDIA_S3_ENDPOINT_URL=...
MEDIA_S3_ACCESS_KEY_ID=...
MEDIA_S3_SECRET_ACCESS_KEY=...
MEDIA_S3_PUBLIC_BASE_URL=...
```

Pode ser usado com provedores compatíveis sem alterar models, rotas de upload ou as chaves salvas no banco.

## Interface comum

Todo backend implementa:

- `save_upload`;
- `exists`;
- `list_stored_paths`;
- `delete`;
- `public_url`.

## URLs e fallback

Para imagens locais, `resolve_image_url` verifica se o arquivo ainda existe. Se o banco aponta para um upload local perdido, a aplicação retorna um asset fallback em vez de uma imagem quebrada.

Para object storage, a resolução não executa `HEAD` por imagem. Isso evita uma chamada remota adicional para cada card/feed/profile. A disponibilidade do objeto deve ser garantida pelo storage/CDN e monitorada operacionalmente.

## Migração futura local -> object storage

A migração não exige alteração no banco desde que os objetos sejam enviados ao bucket preservando a chave `uploads/...`.

Sequência recomendada:

1. escolher o provider;
2. criar bucket e domínio/CDN público;
3. configurar secrets em ambiente de staging;
4. copiar os arquivos existentes preservando as chaves;
5. comparar uma amostra de URLs antigas e novas;
6. validar upload e delete;
7. executar testes exploratórios web/mobile;
8. trocar `MEDIA_STORAGE_BACKEND` para `s3`;
9. monitorar erros e disponibilidade;
10. só então ativar em produção pública.

## Segurança

- nunca versionar access key ou secret;
- usar credencial com escopo mínimo necessário;
- limitar permissões ao bucket de mídia;
- não depender de ACL por objeto;
- preferir domínio/CDN controlado;
- manter validação de tipo, tamanho e conteúdo antes do upload.
