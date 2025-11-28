# Deploying and Sharing Your Documentation

## Overview

Your Sphinx documentation is ready to be viewed, shared, and deployed. Here are several options.

## Option 1: Local Viewing (Simplest)

### Direct File Opening
1. Navigate to: `docs/source/_build/html/`
2. Open `index.html` in your web browser
3. Browse the documentation offline

### Python HTTP Server
1. Open terminal in `docs/source/_build/html/`
2. Run: `python -m http.server 8000`
3. Visit: `http://localhost:8000`
4. Press `Ctrl+C` to stop

### VS Code Live Server
If you have Live Server extension:
1. Right-click on `index.html`
2. Select "Open with Live Server"
3. Documentation opens automatically

## Option 2: Share with Team (Local Network)

### On Your Computer
1. Run: `python -m http.server 8000 --directory docs/source/_build/html`
2. Find your IP address: `ipconfig getifaddr en0` (Mac) or `ipconfig` (Windows)
3. Share the URL with team members: `http://<YOUR_IP>:8000`
4. Team members can visit from their browsers

### Important Notes
- Ensure firewall allows port 8000
- Works only while your computer is running
- All on same network required

## Option 3: GitHub Pages (Public/Private)

### Setup (One-time)
1. Ensure git is initialized in your project
2. Create `gh-pages` branch: 
   ```bash
   git checkout --orphan gh-pages
   git reset --hard
   git commit --allow-empty -m "Initial commit"
   git checkout main
   ```

### Publish Documentation
1. Copy HTML files to a directory:
   ```bash
   xcopy "docs\source\_build\html" "docs_deploy" /E
   ```
2. Push to GitHub:
   ```bash
   git add docs_deploy
   git commit -m "Update documentation"
   git push origin main
   ```
3. In GitHub repository settings:
   - Settings → Pages
   - Select `docs` folder as source
   - Choose `main` branch
   - Enable GitHub Pages

### Access
- Public: `https://<username>.github.io/<repo>/`
- Private: Same URL, but requires login

## Option 4: ReadTheDocs (Recommended for Public Projects)

### Setup
1. Push your code to GitHub/GitLab
2. Visit https://readthedocs.org
3. Sign in with GitHub account
4. Click "Import a Project"
5. Select your repository
6. ReadTheDocs automatically builds on every push

### Advantages
- Automatic updates on push
- Supports multiple versions
- Professional hosting
- Free for open source
- Built-in search

### Your Documentation URL
`https://<projectname>.readthedocs.io/`

## Option 5: Self-Hosted Server

### Using Docker
Create `Dockerfile` in docs folder:
```dockerfile
FROM nginx:alpine
COPY source/_build/html /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build and run:
```bash
docker build -t docs-server docs/
docker run -p 8000:80 docs-server
```

### Using Apache/Nginx
1. Copy `docs/source/_build/html/` to your web server
2. Configure server to serve from that directory
3. Access via your domain

## Option 6: Package as Distribution

### Create Documentation Artifact
```bash
cd docs/source/_build
tar -czf ../../smartmeetingroom-docs.tar.gz html/
```

### Share with Others
1. Upload to shared drive, email, or cloud storage
2. Recipients can extract and view locally
3. No server required

## Option 7: Embed in Project Wiki

### GitHub Wiki
1. Push HTML to a `wiki-docs` branch
2. Reference in GitHub Wiki
3. Embed or link documentation

### GitLab Wiki
1. Create wiki pages
2. Can link to generated documentation
3. Maintain alongside source docs

## Quick Reference

| Method | Setup Time | Hosting | Team Access | Best For |
|--------|-----------|---------|------------|----------|
| Local File | 1 min | None | None | Personal use |
| HTTP Server | 2 min | Your PC | Local network | Quick sharing |
| GitHub Pages | 10 min | GitHub | Public/Private | Open source |
| ReadTheDocs | 5 min | ReadTheDocs | Public | Professional |
| Docker | 10 min | Any server | Any | Production |
| Package | 2 min | Offline | Manual | Distribution |

## Updating Documentation

After code changes:

1. Update docstrings in Python files
2. Rebuild Sphinx:
   ```bash
   cd docs
   python -m sphinx -b html source source/_build/html
   ```
3. Deploy using your chosen method

For GitHub Pages/ReadTheDocs, simply push code and it rebuilds automatically.

## Example: Complete Workflow

### Setup (One-time)
```bash
# 1. Install Sphinx
pip install sphinx sphinx-rtd-theme

# 2. Install service dependencies
pip install -r services/users/requirements.txt
pip install -r services/bookings/requirements.txt

# 3. Build documentation
cd docs
python -m sphinx -b html source source/_build/html

# 4. Test locally
cd source/_build/html
python -m http.server 8000
# Visit http://localhost:8000
```

### Update Workflow
```bash
# 1. Edit code and docstrings
# 2. Rebuild
cd docs
python -m sphinx -b html source source/_build/html

# 3. Commit and push
git add docs/source
git commit -m "Update documentation"
git push origin main
```

## Performance Tips

1. **Caching**: Browser caches HTML, CSS, JS
2. **Compression**: Server can gzip HTML for smaller downloads
3. **CDN**: Use CDN for static assets if hosting large number of users
4. **Search**: Pre-built search index improves search performance

## Customization

### Modify Appearance
Edit `docs/source/conf.py`:
```python
html_theme_options = {
    'collapse_navigation': False,
    'logo_only': False,
    'display_version': True,
}
```

### Add Custom CSS
Place CSS in `docs/source/_static/custom.css` and reference in conf.py

### Customize Layout
Edit templates in `docs/source/_templates/`

## Troubleshooting Deployment

**Problem**: 404 errors when accessing documentation  
**Solution**: Ensure correct path to `index.html`

**Problem**: CSS/images not loading  
**Solution**: Check base URL in `conf.py`, ensure `_static` is served

**Problem**: Search not working  
**Solution**: Rebuild documentation, check browser console for errors

## Support

For issues with specific platforms:
- **GitHub Pages**: https://docs.github.com/en/pages
- **ReadTheDocs**: https://docs.readthedocs.io/
- **Sphinx**: https://www.sphinx-doc.org/

---

Choose the deployment method that best fits your needs. For a development team, HTTP Server or GitHub Pages is recommended. For public projects, ReadTheDocs is ideal.
