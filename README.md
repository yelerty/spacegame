# Retro Space Shooter 🚀

A classic space shooter game built with Pygame, featuring AI auto-pilot, boss battles, power-ups, and stunning particle effects!

## Play Online 🌐

This game can be played directly in your web browser using Pygbag!

### Option 1: itch.io (Recommended)
1. Build the game (see instructions below)
2. Upload to [itch.io](https://itch.io)
3. Share the link!

### Option 2: GitHub Pages
1. Fork this repository
2. Enable GitHub Pages in Settings
3. Build and upload the game files
4. Access at `https://[username].github.io/space_game/`

## Building for Web 🔧

### Prerequisites
```bash
pip install pygbag
```

### Build Steps
```bash
# Navigate to game directory
cd /path/to/space_game

# Build for web (creates build directory)
pygbag main.py

# The game will open automatically in your browser
# Build files are in: build/web/
```

### Files Needed for Web Deploy
After building, you need these files from `build/web/`:
- `index.html`
- `main.py`
- `craft0.png` (player ship image)
- All generated `.wasm`, `.js`, and `.data` files

## Local Play 🎮

### Option 1: Run Original Version
```bash
python game0.py
```

### Option 2: Run Web Version Locally
```bash
python main.py
```

Both versions are identical in gameplay, but `main.py` uses async/await for web compatibility.

## Controls 🕹️

| Key | Action |
|-----|--------|
| Arrow Keys | Move & Rotate |
| A | AI Auto-Pilot (Smart!) |
| U | Loop (Special Move) |
| B | Bomb (Clear Screen) |
| ESC | Pause |
| H | Help Screen |

## Features ✨

- **Smart AI Mode**: Press 'A' to enable AI auto-pilot that dodges bullets, collects power-ups, and uses special moves strategically
- **Boss Battles**: Epic multi-phase boss fights every 500 points
- **Stage Progression**: Difficulty increases every 200 points
- **Power-ups**:
  - 🟡 Yellow: Weapon Upgrade (up to Level 3)
  - 🟢 Green: Health +1
  - 🔵 Cyan: Shield +1
  - 🟠 Orange: Bomb +1
- **Particle Effects**: Explosions, engine trails, and screen shake
- **High Score Tracking**: Saves your best score locally

## Deployment to itch.io 📤

1. **Build the game**:
   ```bash
   pygbag main.py --build
   ```

2. **Zip the build folder**:
   ```bash
   cd build/web
   zip -r ../../spacegame_web.zip .
   cd ../..
   ```

3. **Upload to itch.io**:
   - Go to https://itch.io/game/new
   - Set "Kind of project" to "HTML"
   - Upload `spacegame_web.zip`
   - Check "This file will be played in the browser"
   - Set viewport dimensions: 832 x 624 (or "Fullscreen button")
   - Publish!

## Deployment to GitHub Pages 📄

1. **Create `docs` directory**:
   ```bash
   mkdir docs
   cp -r build/web/* docs/
   ```

2. **Commit and push**:
   ```bash
   git add docs/
   git commit -m "Add web build for GitHub Pages"
   git push
   ```

3. **Enable GitHub Pages**:
   - Go to repository Settings > Pages
   - Source: Deploy from a branch
   - Branch: `main` / `docs`
   - Save

4. **Access your game**:
   - https://[username].github.io/space_game/

## Technical Details 🔧

- **Engine**: Pygame
- **Resolution**: 416×312 internal, 832×624 display (2× scaling)
- **FPS**: 30
- **Web**: Pygbag (WebAssembly)

## Assets 📦

- `craft0.png` - Player spaceship sprite
- `highscore.json` - Persistent high score storage

## Tips for Web Deployment 💡

1. **Test Locally First**: Run `pygbag main.py` and test in browser before deploying
2. **File Paths**: Ensure all assets (images) are in the same directory as `main.py`
3. **Browser Compatibility**: Best performance in Chrome/Edge
4. **Mobile**: Works on mobile browsers but keyboard required for controls

## Troubleshooting 🔍

**Game doesn't load in browser?**
- Check browser console for errors
- Ensure all image files are present
- Try rebuilding with `pygbag main.py --build`

**Images not showing?**
- Verify `craft0.png` is in the same directory
- Check file paths in code are relative, not absolute

**High score not saving?**
- Web version may have limited localStorage access
- Some browsers block file writes in web apps

## Development 🛠️

### Adding New Features
1. Edit `game0.py` for local testing
2. Copy changes to `main.py` (keep async structure)
3. Test locally: `python main.py`
4. Build for web: `pygbag main.py`

### Async/Await Pattern
The web version requires `await asyncio.sleep(0)` in the main loop to yield control to the browser. This is the only major difference from the desktop version.

## Credits 👨‍💻

Created with ❤️ using Pygame and Pygbag
Built with assistance from Claude Code

---

**Enjoy the game! 🎮 Pull requests welcome!**
