tailwind.config = {
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      backgroundColor: {
        primary: 'var(--background-primary)',
        secondary: 'var(--background-secondary)',
      },
      textColor: {
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted: 'var(--text-muted)',
      },
    },
  },
}

// Theme management
const ThemeManager = {
  themes: ["light", "dark", "night"],

  init() {
    // Get theme from localStorage or system preference
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme && this.themes.includes(savedTheme)) {
      this.setTheme(savedTheme);
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      this.setTheme("dark");
    } else {
      this.setTheme("light");
    }

    // Watch for system theme changes
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", (e) => {
        if (!localStorage.getItem("theme")) {
          this.setTheme(e.matches ? "dark" : "light");
        }
      });
  },

  getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  },

  setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);

    this.themes.forEach(t => {
      const icon = document.querySelector(`[data-theme-icon="${t}"]`);
      if (icon) {
        icon.style.display = t === theme ? "block" : "none";
      }
    });
  },

  cycleTheme() {
    const currentIndex = this.themes.indexOf(this.getCurrentTheme());
    const nextIndex = (currentIndex + 1) % this.themes.length;
    this.setTheme(this.themes[nextIndex]);
  },
};

document.addEventListener("DOMContentLoaded", () => ThemeManager.init());

