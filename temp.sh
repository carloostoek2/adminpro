#!/bin/bash
# debug-pr.sh

PR_NUM=$1

echo "🔍 Diagnóstico del PR #$PR_NUM"
echo ""

echo "1. Verificando GitHub CLI..."
gh --version

echo ""
echo "2. Verificando autenticación..."
gh auth status

echo ""
echo "3. Repositorio actual..."
gh repo view 2>&1 | head -5

echo ""
echo "4. Intentando ver el PR..."
gh pr view $PR_NUM

echo ""
echo "5. Listando PRs disponibles..."
gh pr list | head -10
