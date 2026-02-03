#!/bin/bash
# Quick security check before pushing to GitHub

echo "🔍 Checking for potential secrets..."
echo ""

# Check for actual API keys (not just placeholders)
# Only check code files, not documentation or this script itself
echo "1. Checking for Anthropic API keys (sk-ant-*)..."
if find . -type f \( -name "*.py" -o -name "*.env*" -o -name "*.json" \) \
    -not -path "./.git/*" \
    -exec grep -l "sk-ant-api" {} \; 2>/dev/null | grep -q .; then
    echo "❌ FOUND ANTHROPIC API KEY - DO NOT COMMIT!"
    find . -type f \( -name "*.py" -o -name "*.env*" -o -name "*.json" \) \
        -not -path "./.git/*" \
        -exec grep -H "sk-ant-api" {} \;
    exit 1
else
    echo "✅ No Anthropic API keys found"
fi

echo ""
echo "2. Checking for OpenAI API keys (sk-proj-*, sk-*)..."
if find . -type f \( -name "*.py" -o -name "*.env*" -o -name "*.json" \) \
    -not -path "./.git/*" \
    -exec grep -l "sk-proj-" {} \; 2>/dev/null | grep -q .; then
    echo "❌ FOUND OPENAI API KEY - DO NOT COMMIT!"
    find . -type f \( -name "*.py" -o -name "*.env*" -o -name "*.json" \) \
        -not -path "./.git/*" \
        -exec grep -H "sk-proj-" {} \;
    exit 1
else
    echo "✅ No OpenAI API keys found"
fi

echo ""
echo "3. Checking for .env files..."
if find . -name ".env*" -not -path "./.git/*" | grep -q .; then
    echo "⚠️  Found .env files:"
    find . -name ".env*" -not -path "./.git/*"
    echo "   Make sure these are in .gitignore!"
else
    echo "✅ No .env files found"
fi

echo ""
echo "4. Checking for hardcoded secrets patterns..."
if grep -rE "(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]+['\"]" . \
    --exclude-dir=".git" \
    --exclude="*.md" \
    --exclude="check_secrets.sh" \
    --exclude="*.json" 2>/dev/null | grep -v "your-key-here" | grep -v "my-key" | grep -q .; then
    echo "⚠️  Found potential hardcoded secrets:"
    grep -rE "(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]+['\"]" . \
        --exclude-dir=".git" \
        --exclude="*.md" \
        --exclude="check_secrets.sh" \
        --exclude="*.json" 2>/dev/null | grep -v "your-key-here" | grep -v "my-key"
    echo ""
    echo "   Review these carefully!"
else
    echo "✅ No hardcoded secrets found"
fi

echo ""
echo "5. Checking .gitignore exists..."
if [ -f .gitignore ]; then
    echo "✅ .gitignore exists"
    if grep -q "\.env" .gitignore; then
        echo "✅ .gitignore includes .env files"
    else
        echo "⚠️  .gitignore doesn't include .env files!"
    fi
else
    echo "❌ NO .gitignore FILE - CREATE ONE!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Security check complete!"
echo "=========================================="
echo ""
echo "Safe to push to GitHub."
echo ""
