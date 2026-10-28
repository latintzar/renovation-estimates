import Link from "next/link";
import { Check, ArrowRight, Play, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PhoneFrame, DesktopFrame, MockPropertyAnalysis, MockViewingChecklist, MockRenovationTiers, VoiceWaveform, MockEmailAlert, MockRenovationModal } from "./phone-mockups";

export const HomebuyerContent = () => {
  return (
    <div className="animate-in fade-in duration-500">
        {/* Hero Section */}
        <section className="max-w-3xl mx-auto px-6 text-center mb-24 md:mb-32">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 text-xs font-medium text-stone-600 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Your AI Home Advisor
          </div>
          
          <h1 className="font-serif text-4xl md:text-6xl lg:text-7xl leading-[1.1] md:leading-[1.1] tracking-tight mb-8 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
            Tell Leo how you live — <br className="hidden md:block" />
            <span className="text-stone-500 italic">he finds the homes worth rearranging your day for.</span>
          </h1>
          
          {/* Hero Waveform */}
          <div className="mb-10 flex justify-center animate-in fade-in slide-in-from-bottom-8 duration-700 delay-150">
             <VoiceWaveform />
          </div>

          <p className="text-lg md:text-xl text-stone-600 leading-relaxed max-w-2xl mx-auto mb-10 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
            Leo listens to what you want, learns how you live, and scans thousands of new properties every day. 
            He only alerts you when a place is genuinely worth your attention — not the noisy, generic stuff on portals.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in fade-in slide-in-from-bottom-10 duration-700 delay-300">
            <Button size="lg" className="rounded-full px-8 py-6 text-lg bg-stone-900 hover:bg-stone-800 text-white w-full sm:w-auto shadow-lg shadow-stone-900/10">
              Find homes with Leo <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
            <p className="text-sm text-stone-500 mt-4 sm:mt-0">
              No doomscrolling. No wasted viewings. No missed gems.
            </p>
          </div>
        </section>

        {/* Hero Statement */}
        <section className="max-w-4xl mx-auto px-6 mb-32">
          <div className="bg-white rounded-3xl p-8 md:p-12 shadow-sm border border-stone-100">
            <h2 className="font-serif text-3xl md:text-4xl mb-6 leading-tight">
              I’ll find the places you’d drop everything to see.
            </h2>
            <div className="prose prose-lg prose-stone text-stone-600">
              <p>
                Tell me about your life — your routines, your commute, who you see, what you do on weekends, and the kind of space you need to feel right.
              </p>
              <p>
                Every day I analyse new listings, study the neighbourhood, cross‑check legal reality, detect hidden risks, and surface only the properties that truly match you.
              </p>
            </div>
            
            <div className="mt-8 flex items-center gap-4">
              <div className="flex -space-x-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="w-8 h-8 rounded-full bg-stone-200 border-2 border-white flex items-center justify-center text-[10px] font-bold text-stone-500">
                    {String.fromCharCode(64 + i)}
                  </div>
                ))}
              </div>
              <div className="text-sm font-medium text-stone-900">
                “Leo felt like having a brutally honest buyer’s agent sitting on my shoulder — but better.”
              </div>
            </div>
          </div>
        </section>

        {/* The Promise - Steps */}
        <section id="how-it-works" className="max-w-6xl mx-auto px-6 mb-32">
          
          {/* Step 1 */}
          <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-center mb-32">
            <div className="relative group">
              <div className="absolute -left-12 top-0 text-6xl font-serif text-stone-100 -z-10 group-hover:text-stone-200 transition-colors">1</div>
              <h3 className="font-serif text-2xl mb-4">Tell Leo how you live</h3>
              <p className="text-stone-600 leading-relaxed mb-6">
                A short conversation to understand what you value, how you move through the city, what bothers you, what excites you, and what “home” actually means to you.
              </p>
            </div>
             <div className="flex justify-center items-center h-[400px] bg-stone-100/50 rounded-[2.5rem] border border-stone-200 relative overflow-hidden">
                 {/* Chat / Waveform Visual */}
                 <div className="absolute inset-0 flex flex-col items-center justify-center p-8">
                    <div className="w-full max-w-md space-y-6">
                        {/* Speech Bubble 1 */}
                        <div className="bg-white p-4 rounded-2xl rounded-bl-none shadow-sm border border-stone-100 self-start max-w-[80%] animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <p className="text-sm text-stone-600">I need lots of natural light for my plants.</p>
                        </div>
                        
                        {/* Speech Bubble 2 */}
                        <div className="bg-white p-4 rounded-2xl rounded-bl-none shadow-sm border border-stone-100 self-start max-w-[80%] animate-in fade-in slide-in-from-bottom-2 duration-500 delay-100">
                            <p className="text-sm text-stone-600">And I work from home, so a quiet street is non-negotiable.</p>
                        </div>

                        {/* Leo Waveform */}
                        <div className="flex items-center gap-4 mt-8 self-center">
                            <div className="w-10 h-10 rounded-full bg-stone-900 flex items-center justify-center text-white font-serif text-lg">L</div>
                            <VoiceWaveform />
                        </div>
                         <div className="bg-stone-900 text-white p-4 rounded-2xl rounded-tl-none shadow-md self-end max-w-[80%] animate-in fade-in slide-in-from-bottom-2 duration-500 delay-300">
                            <p className="text-sm">Got it. Focusing on high-floor apartments in low-traffic zones like Gracia and Eixample Dret.</p>
                        </div>
                    </div>
                 </div>
             </div>
          </div>

          {/* Step 2 */}
          <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-center mb-32">
             <div className="flex justify-center order-2 md:order-1">
                 <PhoneFrame className="shadow-2xl">
                    <MockEmailAlert />
                 </PhoneFrame>
             </div>
             <div className="relative group order-1 md:order-2">
                <div className="absolute -left-12 top-0 text-6xl font-serif text-stone-100 -z-10 group-hover:text-stone-200 transition-colors">2</div>
                <h3 className="font-serif text-2xl mb-4">Get daily home alerts worth seeing</h3>
                <p className="text-stone-600 leading-relaxed">
                  I scan new listings in real time and filter out the noise.
                  I only send the ones that match your lifestyle, your commute, your vibe, your budget, and your appetite for renovation.
                </p>
             </div>
          </div>

          {/* Step 3 - Analysis Screenshot */}
          <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-center mb-32">
            <div className="relative group">
              <div className="absolute -left-12 top-0 text-6xl font-serif text-stone-100 -z-10 group-hover:text-stone-200 transition-colors">3</div>
              <h3 className="font-serif text-2xl mb-4">Know why it matters — before you see photos</h3>
              <p className="text-stone-600 mb-6">I share the crucial context you can’t get from photos:</p>
              <ul className="space-y-3 text-sm text-stone-600">
                {[
                  "Construction era structural concerns",
                  "Legal vs actual surface area",
                  "Street noise & Airbnb saturation",
                  "Gentrification & public works",
                  "Neighbourhood fit for your week",
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <Check className="w-4 h-4 text-stone-400 mt-0.5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm italic text-stone-500">If a property passes these checks and interests you, I dive deeper.</p>
            </div>
            <div className="flex justify-center">
                 <PhoneFrame>
                    <MockPropertyAnalysis />
                 </PhoneFrame>
            </div>
          </div>

          {/* Step 4 - Checklist Screenshot */}
          <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-center mb-32">
            <div className="flex justify-center order-2 md:order-1">
                 <PhoneFrame>
                    <MockViewingChecklist />
                 </PhoneFrame>
            </div>
            <div className="relative group order-1 md:order-2">
              <div className="absolute -left-12 top-0 text-6xl font-serif text-stone-100 -z-10 group-hover:text-stone-200 transition-colors">4</div>
              <h3 className="font-serif text-2xl mb-4">I arrange the viewing and coach you through it</h3>
              <p className="text-stone-600 leading-relaxed mb-6">
                I’ll WhatsApp the agent, coordinate times, and send you a personalised viewing checklist: what to ask, what to test, what to look for. After the visit, I’ll follow up to refine your preferences.
              </p>
            </div>
          </div>

          {/* Step 5 - Renovation Screenshot (Desktop Width Modal) */}
          <div className="grid grid-cols-1 gap-12 items-center">
            <div className="relative group max-w-2xl">
              <div className="absolute -left-12 top-0 text-6xl font-serif text-stone-100 -z-10 group-hover:text-stone-200 transition-colors">5</div>
              <h3 className="font-serif text-2xl mb-4">Plan your renovation with confidence</h3>
              <p className="text-stone-600 leading-relaxed mb-6">
                 For homes you love, I go a step further. I sketch potential layouts, estimate costs for different renovation tiers, flag permits you’ll need, and highlight structural or logistical constraints. You stay in control — I give you the vision, the numbers and the questions to ask contractors.
              </p>
               <Button className="rounded-full px-6 bg-stone-900 text-white hover:bg-stone-800">
                Get started
              </Button>
            </div>
            
            {/* Full Width Desktop Mockup for Renovation Modal */}
            <div className="w-full">
                 <DesktopFrame className="h-[600px] shadow-2xl">
                    <MockRenovationModal />
                 </DesktopFrame>
            </div>
          </div>
        </section>

        {/* Why Talk to Leo (Comparison) */}
        <section id="comparison" className="max-w-5xl mx-auto px-6 mb-32">
          <div className="text-center mb-16">
            <h2 className="font-serif text-3xl md:text-4xl mb-6">Why talk to Leo?</h2>
          </div>

          <div className="overflow-hidden rounded-2xl border border-stone-200 shadow-sm bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm min-w-[600px]">
                <thead>
                  <tr className="bg-stone-50 border-b border-stone-100">
                    <th className="p-4 pl-6 font-medium text-stone-500 w-1/4"></th>
                    <th className="p-4 font-serif text-lg font-medium text-stone-900 w-1/4 bg-stone-100/50">Leo</th>
                    <th className="p-4 font-medium text-stone-400 w-1/4">Portals</th>
                    <th className="p-4 font-medium text-stone-400 w-1/4">Agents</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Fit</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Learns your life</td>
                    <td className="p-4 text-stone-500">Broad filters</td>
                    <td className="p-4 text-stone-500">Seller‑focused</td>
                  </tr>
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Insight</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Contextual + Visual intelligence</td>
                    <td className="p-4 text-stone-500">Photos + price</td>
                    <td className="p-4 text-stone-500">Sales pitch</td>
                  </tr>
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Risk checks</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Noise, legality, geology, neighbour complaints, public works</td>
                    <td className="p-4 text-stone-500">None</td>
                    <td className="p-4 text-stone-500">None</td>
                  </tr>
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Viewing help</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Checklist + questions</td>
                    <td className="p-4 text-stone-500">None</td>
                    <td className="p-4 text-stone-500">Minimal</td>
                  </tr>
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Follow‑up</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Learns from you, updates your model</td>
                    <td className="p-4 text-stone-500">You start over</td>
                    <td className="p-4 text-stone-500">Dependent</td>
                  </tr>
                   <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Renovation help</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Sketches, cost estimates, permit hints</td>
                    <td className="p-4 text-stone-500">None</td>
                    <td className="p-4 text-stone-500">None</td>
                  </tr>
                  <tr>
                    <td className="p-4 pl-6 font-medium text-stone-900">Cost</td>
                    <td className="p-4 text-stone-900 font-medium bg-stone-50/30">Free (for now)</td>
                    <td className="p-4 text-stone-500">Free</td>
                    <td className="p-4 text-stone-500">Hidden fees</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Testimonials (Love Letters) */}
        <section id="reviews" className="max-w-6xl mx-auto px-6 mb-32">
          <h2 className="font-serif text-3xl md:text-4xl text-center mb-16">Love Letters</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              "Leo asked questions I’d never been asked about property — suddenly I understood what I actually want in a home.",
              "The alerts feel magical. They’re so much better than Idealista filters.",
              "Leo told me why a flat was a red flag before I got excited — I didn’t realise how many traps I was avoiding.",
              "It feels like a friend walking the city with me. The recommendations are weirdly spot‑on.",
              "Using Leo is the first time I’ve felt guided, not overwhelmed."
            ].map((quote, i) => (
              <div key={i} className="bg-white p-8 rounded-2xl shadow-sm border border-stone-100 hover:shadow-md transition-shadow">
                <div className="text-amber-400 text-xl mb-4">★★★★★</div>
                <p className="text-stone-700 leading-relaxed">“{quote}”</p>
              </div>
            ))}
          </div>
        </section>

        {/* How Leo Works (Explainer) */}
        <section className="max-w-4xl mx-auto px-6 mb-32">
          <div className="bg-stone-900 text-white rounded-3xl overflow-hidden shadow-2xl">
            <div className="p-8 md:p-16 text-center">
              <h2 className="font-serif text-3xl md:text-4xl mb-8">How Leo Works</h2>
              
              <div className="relative inline-flex items-center justify-center w-20 h-20 rounded-full bg-white/10 hover:bg-white/20 transition-colors cursor-pointer mb-8 group">
                <Play className="w-8 h-8 text-white fill-white ml-1 group-hover:scale-110 transition-transform" />
              </div>
              
              <div className="max-w-2xl mx-auto space-y-6 text-stone-300 leading-relaxed text-left md:text-center">
                <p>“Tell me how you live. I’ll listen, learn, and map the parts of the city that truly fit you.</p>
                <p>Every day, I scan new listings, cross‑check the legal reality, inspect the street, analyse complaints from neighbours, and watch for early signs of value.</p>
                <p>I only notify you when a place is worth leaving your plans for.</p>
                <p>When you like a place, I arrange the viewing and coach you through it.</p>
                <p>If it fits, I help you visualise renovation possibilities and understand the costs and permits.</p>
                <p>I’m here for your entire journey.”</p>
              </div>
            </div>
          </div>
        </section>

        {/* Actual Buyer Value */}
        <section className="max-w-6xl mx-auto px-6 mb-32">
           <div className="text-center mb-16">
            <h2 className="font-serif text-3xl md:text-4xl mb-4">I find the homes portals can't show you.</h2>
            <p className="text-stone-500">The data underneath the listing.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 md:gap-12">
            
            {/* The Hidden Risks */}
            <div className="bg-stone-50 rounded-2xl p-8 border border-stone-100">
              <h3 className="font-serif text-xl mb-6 flex items-center gap-2">
                <Info className="w-5 h-5 text-stone-400" /> Hidden Risks
              </h3>
              <ul className="space-y-3">
                {[
                  "incorrect m²",
                  "illegal extensions",
                  "noisy streets",
                  "thin walls",
                  "bars underneath",
                  "Airbnb hotspots",
                  "upcoming streetworks",
                  "humidity risk",
                  "low natural light",
                  "structural hints"
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-stone-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400/50"></span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* The Wildcards */}
            <div className="bg-stone-50 rounded-2xl p-8 border border-stone-100">
              <h3 className="font-serif text-xl mb-6 flex items-center gap-2">
                 <span className="text-amber-400">✦</span> Wildcards
              </h3>
              <ul className="space-y-3">
                {[
                  "mispriced gems",
                  "ageing owners",
                  "listings written badly",
                  "“sleepers” in good streets",
                  "good bones + cheap renovations",
                  "soon‑to‑be pedestrianised zones",
                  "one floor off from perfect"
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-stone-600">
                     <span className="w-1.5 h-1.5 rounded-full bg-amber-400/50"></span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

             {/* The Fit */}
             <div className="bg-stone-50 rounded-2xl p-8 border border-stone-100">
              <h3 className="font-serif text-xl mb-6 flex items-center gap-2">
                 <span className="text-green-400">♥</span> The Fit
              </h3>
              <ul className="space-y-3">
                {[
                  "commute alignment",
                  "weekend hotspots",
                  "gym/friends proximity",
                  "hosting potential",
                  "sunlight pattern",
                  "vibe‑matching"
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-stone-600">
                     <span className="w-1.5 h-1.5 rounded-full bg-green-400/50"></span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            
          </div>
        </section>

        {/* Final CTA */}
        <section className="max-w-3xl mx-auto px-6 text-center mb-32">
          <h2 className="font-serif text-4xl md:text-5xl mb-8">Ready to see what you’ve been missing?</h2>
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-stone-100 inline-block mb-10">
            <p className="text-xl text-stone-600 italic">
              “I’ll ask a few questions, learn your vibe, and start scanning the city for you.”
            </p>
          </div>
          <br />
          <Button size="lg" className="rounded-full px-10 py-8 text-xl bg-stone-900 text-white hover:bg-stone-800 shadow-xl shadow-stone-900/10">
            Talk to Leo
          </Button>
        </section>
    </div>
  );
};
