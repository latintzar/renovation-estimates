"use client";

/**
 * ListingReview Component
 * =======================
 * 
 * Full-screen review UI for scraped property data.
 * Allows user to edit fields before saving.
 */

import { useState } from "react";
import Image from "next/image";
import { 
  ChevronLeft, 
  ChevronRight, 
  Edit2, 
  Check, 
  X,
  Bed,
  Bath,
  Maximize,
  MapPin,
  Building2,
  Building,
  FileText
} from "lucide-react";
import { cn } from "@/lib/utils";
import { 
  type ScrapedData, 
  formatPrice, 
  getDomainConfig 
} from "@/lib/types";

interface ListingReviewProps {
  data: ScrapedData;
  sourceUrl: string;
  onConfirm: (data: ScrapedData) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function ListingReview({
  data: initialData,
  sourceUrl,
  onConfirm,
  onCancel,
  isLoading = false,
}: ListingReviewProps) {
  const [data, setData] = useState<ScrapedData>(initialData);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");

  const domainConfig = getDomainConfig(sourceUrl);
  const photos = data.image_urls || [];

  // Photo navigation
  const nextPhoto = () => {
    if (photos.length > 0) {
      setCurrentPhotoIndex((i) => (i + 1) % photos.length);
    }
  };

  const prevPhoto = () => {
    if (photos.length > 0) {
      setCurrentPhotoIndex((i) => (i - 1 + photos.length) % photos.length);
    }
  };

  // Field editing
  const startEdit = (field: string, value: unknown) => {
    setEditingField(field);
    setEditValue(String(value || ""));
  };

  const saveEdit = () => {
    if (!editingField) return;
    
    const newData = { ...data };
    const numericFields = ["price_eur", "sqm", "bedrooms", "bathrooms"];
    
    if (numericFields.includes(editingField)) {
      (newData as Record<string, unknown>)[editingField] = parseFloat(editValue) || undefined;
    } else {
      (newData as Record<string, unknown>)[editingField] = editValue;
    }
    
    setData(newData);
    setEditingField(null);
    setEditValue("");
  };

  const cancelEdit = () => {
    setEditingField(null);
    setEditValue("");
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/90 backdrop-blur-lg border-b">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={onCancel}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-900 touch-target"
          >
            <X className="w-5 h-5" />
            <span className="hidden sm:inline">Cancel</span>
          </button>
          
          <h1 className="font-semibold text-gray-900">Review Listing</h1>
          
          <button
            onClick={() => onConfirm(data)}
            disabled={isLoading}
            className={cn(
              "flex items-center gap-1 px-4 py-2 rounded-xl font-medium touch-target",
              "bg-brand-500 text-white hover:bg-brand-600",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors"
            )}
          >
            <Check className="w-4 h-4" />
            <span>Confirm</span>
          </button>
        </div>
      </header>

      {/* Photo Gallery */}
      <div className="relative aspect-[4/3] bg-gray-100">
        {photos.length > 0 ? (
          <>
            <Image
              src={photos[currentPhotoIndex]}
              alt={`Photo ${currentPhotoIndex + 1}`}
              fill
              className="object-cover"
              priority
            />
            
            {/* Navigation */}
            {photos.length > 1 && (
              <>
                <button
                  onClick={prevPhoto}
                  className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 text-white rounded-full hover:bg-black/70"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  onClick={nextPhoto}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 text-white rounded-full hover:bg-black/70"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </>
            )}
            
            {/* Counter */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-3 py-1 bg-black/60 text-white text-sm rounded-full">
              {currentPhotoIndex + 1} / {photos.length}
            </div>
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            No photos available
          </div>
        )}
        
        {/* Domain Badge */}
        {domainConfig && (
          <div className={cn(
            "absolute top-4 left-4 px-3 py-1.5 rounded-full text-sm font-medium",
            domainConfig.bgClass,
            domainConfig.textClass
          )}>
            {domainConfig.name}
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {photos.length > 1 && (
        <div className="photo-gallery-thumbs">
          {photos.slice(0, 10).map((url, i) => (
            <button
              key={i}
              onClick={() => setCurrentPhotoIndex(i)}
              className={cn(
                "photo-gallery-thumb",
                i === currentPhotoIndex && "active"
              )}
            >
              <Image
                src={url}
                alt={`Thumb ${i + 1}`}
                fill
                className="object-cover"
              />
            </button>
          ))}
          {photos.length > 10 && (
            <div className="w-16 h-16 flex-shrink-0 rounded-lg bg-gray-100 flex items-center justify-center text-xs text-gray-500">
              +{photos.length - 10}
            </div>
          )}
        </div>
      )}

      {/* Property Info */}
      <div className="p-4 space-y-6">
        {/* Price */}
        <EditableField
          label="Price"
          value={data.price_eur}
          displayValue={formatPrice(data.price_eur)}
          field="price_eur"
          editing={editingField}
          editValue={editValue}
          onStartEdit={startEdit}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onChange={setEditValue}
          className="text-3xl font-bold"
        />

        {/* Title */}
        <EditableField
          label="Title"
          value={data.title}
          field="title"
          editing={editingField}
          editValue={editValue}
          onStartEdit={startEdit}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onChange={setEditValue}
          className="text-xl font-semibold"
        />

        {/* Location */}
        <div className="flex items-start gap-3">
          <MapPin className="w-5 h-5 text-gray-400 mt-0.5" />
          <div className="flex-1 space-y-2">
            <EditableField
              label="Address"
              value={data.address}
              field="address"
              editing={editingField}
              editValue={editValue}
              onStartEdit={startEdit}
              onSave={saveEdit}
              onCancel={cancelEdit}
              onChange={setEditValue}
            />
            <div className="flex gap-4">
              <EditableField
                label="City"
                value={data.city}
                field="city"
                editing={editingField}
                editValue={editValue}
                onStartEdit={startEdit}
                onSave={saveEdit}
                onCancel={cancelEdit}
                onChange={setEditValue}
                inline
              />
              <EditableField
                label="Region"
                value={data.region}
                field="region"
                editing={editingField}
                editValue={editValue}
                onStartEdit={startEdit}
                onSave={saveEdit}
                onCancel={cancelEdit}
                onChange={setEditValue}
                inline
              />
            </div>
          </div>
        </div>

        {/* Key Stats */}
        <div className="grid grid-cols-3 gap-4 py-4 border-y">
          <StatField
            icon={<Maximize className="w-5 h-5" />}
            label="Size"
            value={data.sqm}
            suffix="m²"
            field="sqm"
            editing={editingField}
            editValue={editValue}
            onStartEdit={startEdit}
            onSave={saveEdit}
            onCancel={cancelEdit}
            onChange={setEditValue}
          />
          <StatField
            icon={<Bed className="w-5 h-5" />}
            label="Bedrooms"
            value={data.bedrooms}
            field="bedrooms"
            editing={editingField}
            editValue={editValue}
            onStartEdit={startEdit}
            onSave={saveEdit}
            onCancel={cancelEdit}
            onChange={setEditValue}
          />
          <StatField
            icon={<Bath className="w-5 h-5" />}
            label="Bathrooms"
            value={data.bathrooms}
            field="bathrooms"
            editing={editingField}
            editValue={editValue}
            onStartEdit={startEdit}
            onSave={saveEdit}
            onCancel={cancelEdit}
            onChange={setEditValue}
          />
        </div>

        {/* Additional Details */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-gray-400" />
            <EditableField
              label="Property Type"
              value={data.property_type}
              field="property_type"
              editing={editingField}
              editValue={editValue}
              onStartEdit={startEdit}
              onSave={saveEdit}
              onCancel={cancelEdit}
              onChange={setEditValue}
              inline
            />
          </div>
          
          {data.floor_level && (
            <div className="flex items-center gap-3">
              <Building className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">{data.floor_level}</span>
              {data.has_elevator !== undefined && (
                <span className="text-gray-500 text-sm">
                  {data.has_elevator ? "• With elevator" : "• No elevator"}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Description */}
        {data.description && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-gray-400" />
              <span className="font-medium text-gray-700">Description</span>
            </div>
            <p className="text-gray-600 text-sm whitespace-pre-line line-clamp-6">
              {data.description}
            </p>
          </div>
        )}

        {/* Features */}
        {data.features && data.features.length > 0 && (
          <div className="space-y-2">
            <span className="font-medium text-gray-700">Features</span>
            <div className="flex flex-wrap gap-2">
              {data.features.slice(0, 10).map((feature, i) => (
                <span key={i} className="feature-pill">
                  {feature}
                </span>
              ))}
              {data.features.length > 10 && (
                <span className="feature-pill bg-gray-200">
                  +{data.features.length - 10} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Editable Field Component
interface EditableFieldProps {
  label: string;
  value: unknown;
  displayValue?: string;
  field: string;
  editing: string | null;
  editValue: string;
  onStartEdit: (field: string, value: unknown) => void;
  onSave: () => void;
  onCancel: () => void;
  onChange: (value: string) => void;
  className?: string;
  inline?: boolean;
}

function EditableField({
  label,
  value,
  displayValue,
  field,
  editing,
  editValue,
  onStartEdit,
  onSave,
  onCancel,
  onChange,
  className,
  inline,
}: EditableFieldProps) {
  const isEditing = editing === field;
  const display = displayValue || String(value || "—");

  if (isEditing) {
    return (
      <div className={cn("flex items-center gap-2", inline && "flex-1")}>
        <input
          type="text"
          value={editValue}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500",
            className
          )}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter") onSave();
            if (e.key === "Escape") onCancel();
          }}
        />
        <button onClick={onSave} className="p-2 text-green-600 hover:bg-green-50 rounded-lg">
          <Check className="w-4 h-4" />
        </button>
        <button onClick={onCancel} className="p-2 text-gray-400 hover:bg-gray-100 rounded-lg">
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => onStartEdit(field, value)}
      className={cn(
        "group flex items-center gap-2 text-left hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 -my-1 transition-colors",
        inline && "flex-1"
      )}
    >
      <span className={cn("text-gray-900", className)}>{display}</span>
      <Edit2 className="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  );
}

// Stat Field Component
interface StatFieldProps {
  icon: React.ReactNode;
  label: string;
  value: unknown;
  suffix?: string;
  field: string;
  editing: string | null;
  editValue: string;
  onStartEdit: (field: string, value: unknown) => void;
  onSave: () => void;
  onCancel: () => void;
  onChange: (value: string) => void;
}

function StatField({
  icon,
  label,
  value,
  suffix = "",
  field,
  editing,
  editValue,
  onStartEdit,
  onSave,
  onCancel,
  onChange,
}: StatFieldProps) {
  const isEditing = editing === field;

  return (
    <div className="text-center">
      <div className="flex justify-center text-gray-400 mb-1">{icon}</div>
      {isEditing ? (
        <div className="flex items-center justify-center gap-1">
          <input
            type="number"
            value={editValue}
            onChange={(e) => onChange(e.target.value)}
            className="w-16 px-2 py-1 text-center border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") onSave();
              if (e.key === "Escape") onCancel();
            }}
          />
          <button onClick={onSave} className="p-1 text-green-600">
            <Check className="w-3 h-3" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => onStartEdit(field, value)}
          className="group"
        >
          <p className="text-xl font-semibold text-gray-900 group-hover:text-brand-600">
            {value ? `${value}${suffix}` : "—"}
          </p>
        </button>
      )}
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

