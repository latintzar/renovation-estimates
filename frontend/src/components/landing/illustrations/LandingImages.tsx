"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * Landing Page Generated Images
 * 
 * These images are generated using Gemini 3 Pro Image Preview
 * and stored in /public/images/landing/
 * 
 * To regenerate: POST /api/landing/generate-images
 */

// Image paths - centralized for easy updates
// All images optimized to WebP for fast loading (originally 240MB PNG → 3.5MB WebP)
export const LANDING_IMAGES = {
  // General
  heroBarcelona: "/images/landing/hero-barcelona-aerial.webp",
  interiorApartment: "/images/landing/interior-spanish-apartment.webp",
  streetNeighborhood: "/images/landing/street-spanish-neighborhood.webp",
  buildingFacade: "/images/landing/building-spanish-facade.webp",
  agentWorkspace: "/images/landing/agent-calm-workspace.webp",
  citySkyline: "/images/landing/city-skyline-relocation.webp",
  // Renters-specific
  rentersMorningLight: "/images/landing/renters-morning-light.webp",
  rentersApartmentSearch: "/images/landing/renters-apartment-search.webp",
  rentersViewingDay: "/images/landing/renters-viewing-day.webp",
  rentersBalconyView: "/images/landing/renters-balcony-view.webp",
  rentersKeysmoment: "/images/landing/renters-keys-moment.webp",
  rentersNeighborhoodLife: "/images/landing/renters-neighborhood-life.webp",
  // Listing vs Reality
  listingStagedBeautiful: "/images/landing/listing-staged-beautiful.webp",
  realityDarkCorner: "/images/landing/reality-dark-corner.webp",
  realityWaterStain: "/images/landing/reality-water-stain.webp",
  realityStreetView: "/images/landing/reality-street-view.webp",
  realityNiceLight: "/images/landing/reality-nice-light.webp",
  propertyCardApartment: "/images/landing/property-card-apartment.webp",
  // Renovation Before/After - Each tier shows a different room
  // Before images (3 different rooms with furniture)
  renoBeforeLiving: "/images/landing/reno-before-living.webp",
  renoBeforeKitchen: "/images/landing/reno-before-kitchen.webp",
  renoBeforeBathroom: "/images/landing/reno-before-bathroom.webp",
  // After images (generated from before images for perfect angle match)
  renoAfterLivingEstandar: "/images/landing/reno-after-living-estandar.webp",
  renoAfterKitchenOptimo: "/images/landing/reno-after-kitchen-optimo.webp",
  renoAfterBathroomPlus: "/images/landing/reno-after-bathroom-plus.webp",
  // Legacy - kept for backwards compatibility
  renoAfterLivable: "/images/landing/reno-after-livable.webp",
  renoAfterComfortable: "/images/landing/reno-after-comfortable.webp",
  renoAfterCompetitive: "/images/landing/reno-after-competitive.webp",
} as const;

interface LandingImageProps {
  src: string;
  alt: string;
  className?: string;
  priority?: boolean;
  fill?: boolean;
  width?: number;
  height?: number;
  overlay?: "dark" | "light" | "gradient" | "none";
  objectFit?: "cover" | "contain" | "fill";
}

/**
 * Optimized landing page image component
 */
export const LandingImage = ({
  src,
  alt,
  className,
  priority = false,
  fill = false,
  width,
  height,
  overlay = "none",
  objectFit = "cover",
}: LandingImageProps) => {
  const overlayClasses = {
    dark: "after:absolute after:inset-0 after:bg-black/30",
    light: "after:absolute after:inset-0 after:bg-white/20",
    gradient: "after:absolute after:inset-0 after:bg-gradient-to-t after:from-stone-900/60 after:via-transparent after:to-transparent",
    none: "",
  };

  return (
    <div className={cn("relative overflow-hidden", overlayClasses[overlay], className)}>
      {fill ? (
        <Image
          src={src}
          alt={alt}
          fill
          priority={priority}
          className={cn("object-cover", objectFit === "contain" && "object-contain")}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 80vw, 70vw"
        />
      ) : (
        <Image
          src={src}
          alt={alt}
          width={width || 800}
          height={height || 600}
          priority={priority}
          className={cn("w-full h-auto")}
        />
      )}
    </div>
  );
};

/**
 * Hero background with Barcelona aerial illustration
 */
export const HeroBackgroundImage = ({ className }: { className?: string }) => (
  <div className={cn("absolute inset-0 -z-10 overflow-hidden", className)}>
    <LandingImage
      src={LANDING_IMAGES.heroBarcelona}
      alt="Stylized aerial view of Barcelona"
      fill
      priority
      overlay="light"
      className="opacity-20"
    />
  </div>
);

/**
 * Interior apartment lifestyle image
 */
export const InteriorImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.interiorApartment}
    alt="Bright Spanish apartment interior with natural light"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Neighborhood street scene
 */
export const NeighborhoodImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.streetNeighborhood}
    alt="Charming walkable Spanish neighborhood street"
    className={cn("rounded-2xl shadow-lg", className)}
    width={600}
    height={450}
  />
);

/**
 * Building facade image
 */
export const BuildingFacadeImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.buildingFacade}
    alt="Traditional Spanish apartment building facade"
    className={cn("rounded-2xl shadow-lg", className)}
    width={450}
    height={600}
  />
);

/**
 * Agent workspace image for professionals
 */
export const AgentWorkspaceImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.agentWorkspace}
    alt="Calm professional workspace"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * City skyline for relocation section
 */
export const CitySkylineImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.citySkyline}
    alt="Mediterranean city skyline"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

// ===== RENTERS-SPECIFIC IMAGES =====

/**
 * Morning light streaming into apartment
 */
export const RentersMorningLightImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersMorningLight}
    alt="Morning light streaming into a Spanish apartment"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Person casually searching on phone
 */
export const RentersSearchImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersApartmentSearch}
    alt="Person casually browsing apartments on phone"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Apartment viewing scene
 */
export const RentersViewingImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersViewingDay}
    alt="Person viewing a bright Spanish apartment"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Barcelona balcony view
 */
export const RentersBalconyImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersBalconyView}
    alt="View from a Barcelona apartment balcony"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Getting the keys moment
 */
export const RentersKeysMomentImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersKeysmoment}
    alt="Receiving keys to a new apartment"
    className={cn("rounded-2xl shadow-lg", className)}
    width={450}
    height={338}
  />
);

/**
 * Neighborhood daily life
 */
export const RentersNeighborhoodImage = ({ className }: { className?: string }) => (
  <LandingImage
    src={LANDING_IMAGES.rentersNeighborhoodLife}
    alt="Daily life in a Barcelona neighborhood"
    className={cn("rounded-2xl shadow-lg", className)}
    width={800}
    height={450}
  />
);

/**
 * Background section with image
 */
export const ImageBackgroundSection = ({
  image,
  children,
  className,
  overlay = "dark",
}: {
  image: keyof typeof LANDING_IMAGES;
  children: React.ReactNode;
  className?: string;
  overlay?: "dark" | "light" | "gradient" | "none";
}) => {
  const overlayClasses = {
    dark: "before:absolute before:inset-0 before:bg-black/40 before:z-0",
    light: "before:absolute before:inset-0 before:bg-white/30 before:z-0",
    gradient: "before:absolute before:inset-0 before:bg-gradient-to-t before:from-stone-900/70 before:via-stone-900/30 before:to-transparent before:z-0",
    none: "",
  };

  return (
    <section className={cn("relative overflow-hidden", overlayClasses[overlay], className)}>
      <Image
        src={LANDING_IMAGES[image]}
        alt=""
        fill
        className="object-cover -z-10"
        sizes="100vw"
      />
      <div className="relative z-10">{children}</div>
    </section>
  );
};

