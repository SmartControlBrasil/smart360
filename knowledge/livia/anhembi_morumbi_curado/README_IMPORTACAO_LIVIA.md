# Pacote de conhecimento - Anhembi Morumbi para LÍVIA

Data: 2026-06-18  
Objetivo: alimentar a base da LÍVIA com chunks curtos e úteis de engenharia, TPM, automação, IA/dados e inovação.

## Como usar

Copie os arquivos `.md` para uma pasta de conhecimento do Smart360, por exemplo:

```bash
mkdir -p knowledge/livia/anhembi_morumbi_curado
cp *.md knowledge/livia/anhembi_morumbi_curado/
```

Depois rode o importador RAG da LÍVIA conforme o comando existente no projeto. Exemplos prováveis:

```bash
.venv/bin/python manage.py import_livia_rag_knowledge
```

ou, se o comando aceitar diretório:

```bash
.venv/bin/python manage.py import_livia_rag_knowledge --source-dir knowledge/livia/anhembi_morumbi_curado
```

## Regra de uso

Estes arquivos são resumos curados. A LÍVIA pode usar como base de atendimento, mas não deve prometer diagnóstico definitivo sem análise técnica.
