import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { PageContainer } from "@/components/shared/PageContainer";
import { homeNavLinks } from "@/lib/constants";
import { classNames } from "@/lib/classNames";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="sticky top-0 z-40 px-3 pt-3">
      <PageContainer>
        <div
          className={classNames(
            "flex items-center justify-between rounded-full border px-5 py-3 transition duration-200",
            scrolled ? "border-line bg-panel/92 shadow-card backdrop-blur" : "border-transparent bg-transparent",
          )}
        >
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-sm font-semibold text-white">P</div>
            <span className="text-lg font-semibold text-ink">Planera</span>
          </Link>
          <nav className="hidden items-center gap-6 lg:flex">
            {homeNavLinks.map((item) => (
              <a key={item.label} href={item.href} className="text-sm text-muted transition hover:text-ink">
                {item.label}
              </a>
            ))}
            <Link to="/app">
              <Button>Open App</Button>
            </Link>
          </nav>
          <Link to="/app" className="lg:hidden">
            <Button size="sm">Open App</Button>
          </Link>
        </div>
      </PageContainer>
    </header>
  );
}
