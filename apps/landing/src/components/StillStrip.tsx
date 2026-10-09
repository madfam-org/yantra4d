import React from 'react';
import type { GalleryItem } from '../lib/gallery';

/**
 * What the `still` tier shows where the 3D stage would be: the same objects,
 * as a horizontal strip of thumbnails that link into the Studio. No WebGL, no
 * three.js, no extra requests beyond the lazy images.
 */
export default function StillStrip({
  items,
  studioUrl,
  caption,
  openLabel,
  hyperobjectLabel,
}: {
  items: GalleryItem[];
  studioUrl: string;
  caption: string;
  openLabel: string;
  hyperobjectLabel: string;
}) {
  return (
    <div
      data-testid="commons-still"
      className="rounded-xl border border-border bg-card/60 p-4 sm:p-6"
    >
      <p className="mb-4 text-sm text-muted-foreground">{caption}</p>
      <ul className="flex gap-4 overflow-x-auto snap-x pb-2 -mx-1 px-1" aria-label={caption}>
        {items.map((p) => (
          <li key={p.slug} className="snap-start shrink-0 w-44 sm:w-52">
            <a
              href={`${studioUrl}/project/${p.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="group block rounded-lg border border-border/60 bg-background/60 overflow-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <div className="aspect-video bg-secondary/30 overflow-hidden">
                <img
                  src={p.thumbnail}
                  alt={p.name}
                  loading="lazy"
                  decoding="async"
                  width="416"
                  height="234"
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                />
              </div>
              <div className="p-3">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold truncate">{p.name}</h3>
                  {p.isHyperobject && (
                    <span className="shrink-0 rounded border border-blue-500/30 bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">
                      {hyperobjectLabel}
                    </span>
                  )}
                </div>
                <span className="text-xs text-primary-readable group-hover:underline">{openLabel} →</span>
              </div>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
