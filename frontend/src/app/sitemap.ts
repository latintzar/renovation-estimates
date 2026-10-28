import { MetadataRoute } from 'next';

const siteUrl = 'https://leo.casa';

export default function sitemap(): MetadataRoute.Sitemap {
  const currentDate = new Date().toISOString();
  
  return [
    // Homepage (redirects to /es)
    {
      url: siteUrl,
      lastModified: currentDate,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    // Spanish version (primary)
    {
      url: `${siteUrl}/es`,
      lastModified: currentDate,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    // English version
    {
      url: `${siteUrl}/en`,
      lastModified: currentDate,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    // Add more pages as they become available
    // Example: listing pages, blog posts, etc.
  ];
}
