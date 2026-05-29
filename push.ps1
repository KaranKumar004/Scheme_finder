# Step 1: Remove .env from git tracking (won't delete the file itself)
git rm --cached .env 2>$null

# Step 2: Make sure .gitignore ignores .env
$gitignore = Get-Content .gitignore -ErrorAction SilentlyContinue
if ($gitignore -notcontains ".env") {
    Add-Content .gitignore "`n.env"
    Write-Host "Added .env to .gitignore"
}

# Step 3: Stage everything
git add .

# Step 4: Commit
git commit -m "Restore working gemini_handler + fix .env tracking"

# Step 5: Push
git push origin main

Write-Host "`n✅ Done! Check Render for deployment."
