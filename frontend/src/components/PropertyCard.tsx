"use client";

/**
 * PropertyCard Component
 * ======================
 * 
 * Compact card for displaying property listings.
 * Shows thumbnail, price, key stats, and pipeline status.
 */

import Image from "next/image";
import Link from "next/link";
import { Bed, Bath, Maximize, MapPin, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { 
  formatPrice, 
  formatSqm, 
  type Listing,
  type PipelineStatus 
} from "@/lib/types";

interface PropertyCardProps {
  listing: Listing;
  className?: string;
}

export function PropertyCard({ listing, className }: PropertyCardProps) {
  const mainPhoto = listing.photos?.[0];
  
  return (
    <Link
      href={`/listing/${listing.id}`}
      className={cn(
        "block property-card",
        "animate-slide-in",
        className
      )}
    >
      {/* Image */}
      <div className="property-card-image">
        {mainPhoto ? (
          <Image
            src={mainPhoto}
            alt={listing.title || "Property"}
            fill
            className="object-cover"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
        ) : (
          <div className="w-full h-full bg-gray-100 flex items-center justify-center">
            <span className="text-gray-400 text-sm">No image</span>
          </div>
        )}
        
        {/* Photo Count Badge */}
        {listing.photos && listing.photos.length > 1 && (
          <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/60 text-white text-xs rounded-full">
            {listing.photos.length} photos
          </div>
        )}
        
        {/* Pipeline Status Badge */}
        <PipelineStatusBadge status={listing.pipeline_status} />
      </div>
      
      {/* Content */}
      <div className="property-card-content">
        {/* Price */}
        <div className="price-badge">
          {formatPrice(listing.price_eur)}
        </div>
        
        {/* Title */}
        <h3 className="font-medium text-gray-900 line-clamp-1">
          {listing.title || "Anuncio de propiedad"}
        </h3>
        
        {/* Location */}
        {(listing.city || listing.address) && (
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <MapPin className="w-3.5 h-3.5" />
            <span className="line-clamp-1">
              {listing.city || listing.address}
            </span>
          </div>
        )}
        
        {/* Stats */}
        <div className="flex items-center gap-4 pt-2">
          {listing.bedrooms && (
            <div className="stat-item">
              <Bed className="w-4 h-4" />
              <span className="text-sm">{listing.bedrooms}</span>
            </div>
          )}
          {listing.bathrooms && (
            <div className="stat-item">
              <Bath className="w-4 h-4" />
              <span className="text-sm">{listing.bathrooms}</span>
            </div>
          )}
          {listing.sqm && (
            <div className="stat-item">
              <Maximize className="w-4 h-4" />
              <span className="text-sm">{formatSqm(listing.sqm)}</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

// Pipeline Status Badge
function PipelineStatusBadge({ status }: { status?: PipelineStatus }) {
  if (!status || status === "scraped") return null;
  
  const styles: Record<PipelineStatus, { bg: string; text: string; label: string }> = {
    scraped: { bg: "bg-gray-100", text: "text-gray-600", label: "Saved" },
    analyzing: { bg: "bg-blue-100", text: "text-blue-700", label: "Analyzing..." },
    complete: { bg: "bg-green-100", text: "text-green-700", label: "Ready" },
    failed: { bg: "bg-red-100", text: "text-red-700", label: "Error" },
  };
  
  const style = styles[status];
  
  return (
    <div className={cn(
      "absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1",
      style.bg,
      style.text
    )}>
      {status === "analyzing" && <Clock className="w-3 h-3 animate-spin" />}
      {style.label}
    </div>
  );
}

// Skeleton loader for PropertyCard
export function PropertyCardSkeleton() {
  return (
    <div className="property-card">
      <div className="property-card-image skeleton" />
      <div className="property-card-content space-y-3">
        <div className="h-7 w-28 skeleton" />
        <div className="h-5 w-full skeleton" />
        <div className="h-4 w-32 skeleton" />
        <div className="flex gap-4 pt-2">
          <div className="h-4 w-12 skeleton" />
          <div className="h-4 w-12 skeleton" />
          <div className="h-4 w-16 skeleton" />
        </div>
      </div>
    </div>
  );
}

