import Link from "next/link";
import { ArrowRight, Check, Sparkles, Users, Calendar, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DesktopFrame, MockAgentDashboard, MockRenovationPlanner } from "./phone-mockups";

export const AgentContent = () => {
  return (
    <div className="animate-in fade-in duration-500">
        {/* Hero Section */}
        <section className="max-w-4xl mx-auto px-6 text-center mb-24 md:mb-32">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-900 text-xs font-medium text-white mb-8">
            <Sparkles className="w-3 h-3 text-amber-300" />
            Buyer Agents & Personal Shoppers
          </div>
          
          <h1 className="font-serif text-4xl md:text-6xl lg:text-7xl leading-[1.1] md:leading-[1.1] tracking-tight mb-8">
            Scale your superpower.
          </h1>
          
          <p className="text-lg md:text-xl text-stone-600 leading-relaxed max-w-2xl mx-auto mb-10">
            Leo is your AI co‑pilot — helping you deliver deeper insight and exceptional service while you focus on people.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" className="rounded-full px-8 py-6 text-lg bg-stone-900 hover:bg-stone-800 text-white w-full sm:w-auto shadow-lg shadow-stone-900/10">
              Start using Leo with your clients <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </div>
        </section>

        {/* Feature 1: Client Management & Recommendations */}
        <section id="dashboard" className="max-w-7xl mx-auto px-6 mb-32">
             <div className="grid lg:grid-cols-2 gap-16 items-center">
                <div className="order-2 lg:order-1">
                    <DesktopFrame>
                         <MockAgentDashboard />
                    </DesktopFrame>
                </div>
                <div className="order-1 lg:order-2 lg:pl-10">
                    <div className="w-12 h-12 rounded-2xl bg-stone-100 flex items-center justify-center mb-6">
                        <Users className="w-6 h-6 text-stone-900" />
                    </div>
                    <h2 className="font-serif text-3xl md:text-4xl mb-6">
                        Manage clients, not spreadsheets.
                    </h2>
                    <p className="text-stone-600 text-lg leading-relaxed mb-8">
                        See all your clients in one command center. Leo tracks their preferences, surfacing new matches automatically.
                    </p>
                    <ul className="space-y-4">
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Smart Shortlists:</strong> Review Leo's top picks before sending them with a single click.</span>
                         </li>
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Context Preservation:</strong> Every note, viewing, and feedback is stored and used to refine future matches.</span>
                         </li>
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Whitelabeled Links:</strong> Share properties with your branding, not a portal link.</span>
                         </li>
                    </ul>
                </div>
             </div>
        </section>

        {/* Feature 2: Renovation Planning */}
         <section id="renovation" className="max-w-7xl mx-auto px-6 mb-32 bg-stone-50 rounded-[3rem] py-20">
             <div className="grid lg:grid-cols-2 gap-16 items-center">
                 <div className="lg:pr-10">
                    <div className="w-12 h-12 rounded-2xl bg-white shadow-sm flex items-center justify-center mb-6">
                        <ClipboardList className="w-6 h-6 text-stone-900" />
                    </div>
                    <h2 className="font-serif text-3xl md:text-4xl mb-6">
                        Renovation insights you can trust.
                    </h2>
                    <p className="text-stone-600 text-lg leading-relaxed mb-8">
                        Don't just show a "fixer-upper". Show the vision. Leo generates renovation concepts, cost tiers, and timelines instantly.
                    </p>
                    <ul className="space-y-4">
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Visual Ideation:</strong> Use AI renders to help clients see potential.</span>
                         </li>
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Contractor Ready:</strong> Export scope, timelines, and permit needs to get accurate quotes faster.</span>
                         </li>
                         <li className="flex gap-3">
                             <Check className="w-5 h-5 text-green-600 shrink-0" />
                             <span className="text-stone-700"><strong>Budget Confidence:</strong> Give clients realistic ranges (Standard vs. Comfort vs. Plus) before they bid.</span>
                         </li>
                    </ul>
                </div>
                <div className="">
                    <DesktopFrame className="shadow-xl">
                         <MockRenovationPlanner />
                    </DesktopFrame>
                </div>
             </div>
        </section>

        {/* Feature 3: Logistics (Text Only for now, or repurpose existing) */}
        <section id="logistics" className="max-w-4xl mx-auto px-6 mb-32 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-stone-100 mb-6">
                 <Calendar className="w-8 h-8 text-stone-900" />
              </div>
              <h2 className="font-serif text-3xl md:text-4xl mb-6">Automate the logistics.</h2>
              <p className="text-stone-600 text-lg leading-relaxed max-w-2xl mx-auto mb-10">
                  Leo coordinates viewing times, generates personalised checklists for clients, and captures their notes via voice or text. You focus on the negotiation.
              </p>
        </section>


        {/* Why work with Leo */}
        <section id="benefits" className="max-w-4xl mx-auto px-6 mb-32">
          <div className="bg-stone-900 text-white rounded-3xl overflow-hidden shadow-2xl">
            <div className="p-8 md:p-16">
              <h2 className="font-serif text-3xl md:text-4xl mb-12 text-center">Why work with Leo?</h2>
              
              <ul className="space-y-6 max-w-2xl mx-auto">
                {[
                  "Stand out with data‑driven advice and unique insights",
                  "Save hours on research and admin every week",
                  "Enhance your client’s confidence and delight",
                  "Keep control of the relationship — Leo works under your brand",
                  "Pay only when you close deals (custom pricing)"
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-4 text-lg text-stone-300">
                    <Check className="w-6 h-6 text-white shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-3xl mx-auto px-6 text-center mb-32">
          <h2 className="font-serif text-4xl md:text-5xl mb-6">Start using Leo with your clients</h2>
          <p className="text-xl text-stone-600 mb-10 max-w-2xl mx-auto">
            Leo is ready today. Let’s talk about how Leo can supercharge your personal shopper practice. Reach out and we’ll help you get started right away — no waiting list.
          </p>
          <Button size="lg" className="rounded-full px-10 py-8 text-xl bg-stone-900 text-white hover:bg-stone-800 shadow-xl shadow-stone-900/10">
            Contact Us to Get Started
          </Button>
        </section>
    </div>
  );
};
