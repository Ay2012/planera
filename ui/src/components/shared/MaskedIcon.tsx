import type { CSSProperties } from "react";
import { classNames } from "@/lib/classNames";

interface MaskedIconProps {
  src: string;
  className?: string;
}

export function MaskedIcon({ src, className }: MaskedIconProps) {
  const style = {
    WebkitMaskImage: `url(${src})`,
    maskImage: `url(${src})`,
    WebkitMaskRepeat: "no-repeat",
    maskRepeat: "no-repeat",
    WebkitMaskPosition: "center",
    maskPosition: "center",
    WebkitMaskSize: "contain",
    maskSize: "contain",
  } satisfies CSSProperties;

  return <span aria-hidden="true" className={classNames("inline-block shrink-0 bg-current", className)} style={style} />;
}
