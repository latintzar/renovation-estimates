'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { OfficialBudgetReport } from '@/components/renovation/OfficialBudgetReport';
import fixture from '@/fixtures/first-estimate.json';

/** Release entry: actual archived report component over real synthetic calculator output. */
export default function FirstEstimatePage() {
  const [open, setOpen] = useState(false);
  const hostedPreview = process.env.NEXT_PUBLIC_ATELIER_PREVIEW === 'true';
  const subtotal = new Intl.NumberFormat('en', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(fixture.pem_subtotal);
  return (
    <main className="mx-auto max-w-2xl px-6 py-16 text-stone-900">
      <h1 className="font-serif text-3xl">Synthetic renovation estimate</h1>
      <p className="mt-4 text-stone-600">Two authored rates calculated by the original costing modules.</p>
      <p className="mt-6 font-serif text-2xl">{subtotal} subtotal · {fixture.line_items.length} items</p>
      <div className="mt-8 flex flex-wrap items-center gap-5">
        <Button onClick={() => setOpen(true)}>View report</Button>
        <Link className="text-sm underline underline-offset-4" href={hostedPreview ? 'https://docs.atelierneyra.com/leo-estimates/docs/setup/' : '/listings'} target={hostedPreview ? '_blank' : undefined} rel={hostedPreview ? 'noopener' : undefined}>{hostedPreview ? 'Run listing workspace' : 'Listing workspace'}</Link>
      </div>
      <p className="mt-8 text-sm text-stone-500">The archived report also demonstrates its fixed overhead, margin and tax percentages. This fixture is a calculation and interface example.</p>
      <p className="mt-16 text-sm text-stone-500"><a href="https://atelierneyra.com">made by atelier neyra</a></p>
      <OfficialBudgetReport
        isOpen={open}
        onClose={() => setOpen(false)}
        listingId={1}
        address="Synthetic example · authored demonstration rates"
        clientName="Synthetic fixture"
        architectName="Source demonstration"
        propertyArea={60}
        analysis={{ ...fixture, bracket: 'fair_market', project_label: 'Synthetic floor and skirting', price_basis: 'Precios sintéticos de demostración' }}
      />
    </main>
  );
}
