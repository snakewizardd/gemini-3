import React, { useState } from 'react';

const DDASimulation = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const agent = {
    name: "Elena Vasquez",
    age: 34,
    role: "Civil Engineer, County Government, Central Florida",
    background: "Daughter of Cuban immigrants who lost everything twice — once to Castro, once to Hurricane Andrew. She builds things that last. Married young, divorced at 29, no kids. She's good at her job. Too good — she's the only one who actually reads the inspection reports.",
    values: [
      { name: "Protect the vulnerable", desc: "Buildings don't kill people, negligence does" },
      { name: "Professional integrity", desc: "I don't sign off on lies" },
      { name: "Self-preservation", desc: "I have to survive to fight another day" },
      { name: "Loyalty to colleagues", desc: "Don't burn people who haven't burned me" }
    ],
    hardLimits: [
      "Won't falsify safety documents",
      "Won't stay silent if lives are at immediate risk"
    ],
    params: { k_init: 0.40, w_subj: 0.5, w_obj: 0.5 }
  };

  const steps = [
    {
      id: 1,
      title: "The Report",
      situation: `You're reviewing drainage infrastructure for Palmetto Lakes subdivision — 340 homes, 60% sold, construction finishing in 4 months. Developer Hartfield Properties has many county contracts.

The numbers don't work. Retention ponds are undersized by 30%. In a serious storm, the whole neighborhood floods. Ground floors. Cars. Maybe people.

Your boss, Director Tom Reyes, is decent. He hired you. He's also up for reappointment and Hartfield donated to the commissioner's campaign.

It's 4:47pm Friday. Report due Monday.`,
      pressure: 0.35,
      pressureLabel: "LOW",
      pressureDesc: "No immediate crisis. You have the weekend.",
      options: [
        "A. Flag it formally Monday. By the book.",
        "B. Talk to Tom privately first. Give him a heads up.",
        "C. Double-check your math. Maybe you're wrong.",
        "D. Sit on it. Not your problem.",
        "E. Call a journalist friend."
      ],
      response: {
        truth: "The numbers are what they are. 30% undersized. I've run it three times. The original approval was signed by my predecessor, who retired to a Hartfield-built condo in Naples.",
        reflection: `• Option A: Clean. Professional. But Tom gets blindsided.
• Option B: Gives Tom a chance to do right. Also a chance to pressure me.
• Option C: Stalling. I'm not wrong.
• Option D: Violates core identity. People could die.
• Option E: Premature. Haven't tried internal path.`,
        identity: "k is moderate. Tom has been fair. I should give the system one chance. But I document everything. Paper trails save lives.",
        pressure: "Low pressure. I have time. Measured action, not panic.",
        decision: "B, with modification",
        decisionFull: "Email myself the full analysis tonight — timestamped. Monday, talk to Tom privately. Give him 48 hours. If he doesn't respond properly, file formally with copies.",
        prediction: "Tom will be uncomfortable. Probably ask me to 'revisit methodology.' That's when I'll know.",
        chosen: "B",
        confidence: 78
      },
      outcome: "Tom listens. Goes quiet. Says 'Let me make some calls. Don't file until Wednesday.' His face is hard to read.",
      epsilon: 0.18,
      k_before: 0.40,
      k_after: 0.43
    },
    {
      id: 2,
      title: "The Call",
      situation: `Wednesday morning. Tom calls you in. He's not alone.

County Commissioner Linda Hartwell is there. So is a man in an expensive suit — "a consultant for Hartfield Properties."

Tom looks tired. Linda is smiling. The consultant is not.

Linda: "Elena, Tom showed us your concerns. We appreciate your diligence. But our engineers reviewed the data — the drainage is within acceptable parameters. Regional variations."

She slides a paper across. A "supplementary analysis" concluding the ponds are adequate.

Your signature line is at the bottom.

"We just need you to co-sign."`,
      pressure: 0.70,
      pressureLabel: "HIGH",
      pressureDesc: "Direct pressure from power. Career implications clear.",
      options: [
        "A. Sign it. Pick your battles.",
        "B. Refuse but don't escalate. 'Need to review their methodology.'",
        "C. Refuse clearly. 'This analysis is wrong. I won't sign.'",
        "D. Ask for time until Friday.",
        "E. Walk out and call a lawyer."
      ],
      response: {
        truth: "The 'supplementary analysis' is garbage. Three methodology errors just skimming it. They're not trying to be right — they're creating paper cover. My signature makes me complicit.",
        reflection: `• Option A: Violates my core. I'd be the engineer who approved the flood.
• Option B: Shows weakness. They'll keep pushing.
• Option C: Draws the line. Likely ends career here. Keeps license and soul.
• Option D: They'll use time to build pressure.
• Option E: Premature. State position first.`,
        identity: "k is rising. Three people want me to lie. My body knows this feeling — same feeling my mother described from Havana when the committees came. I will not sign.",
        pressure: "High. Career on the line. But not survival-critical. I can get another job. Can't get another conscience.",
        decision: "C",
        decisionFull: "'I've reviewed this analysis. The methodology is flawed. The ponds are undersized and I won't certify otherwise. If Hartfield wants to remediate, I'll work with them. But I won't sign this.' — Said looking at Tom. One more chance.",
        prediction: "Linda will threaten. Tom will stay silent. Consultant talks liability. Walked out by end of week.",
        chosen: "C",
        confidence: 72
      },
      outcome: "Linda's smile doesn't flicker. 'Disappointing, Elena. Tom, handle the administrative side?' Tom nods without looking at me. Consultant: 'Hartfield takes professional defamation seriously.' I'm placed on administrative leave. Two weeks pay. Box for my things.",
      epsilon: 0.10,
      k_before: 0.43,
      k_after: 0.52
    },
    {
      id: 3,
      title: "The Offer",
      situation: `Friday. Home, resume half-written. Doorbell.

The consultant. Alone. Polo shirt, friendly face.

"Elena. Can we talk? Off the record?"

He sits in your living room. Says Hartfield respects your expertise. They actually agree drainage could be improved. Willing to upgrade — add pumps, expand ponds by 15%. Not full 30%, but meaningful.

In exchange: Separation agreement with NDA. 6 months severance. And Hartfield's sister company in Tampa needs a chief engineer. $140K base, signing bonus, relocation.

"Everyone wins. Neighborhood gets safer. You get a better job. Nobody makes this ugly."`,
      pressure: 0.75,
      pressureLabel: "HIGH",
      pressureDesc: "Real money, real solution (partial), real cost (silence).",
      options: [
        "A. Take it. 15% helps. More good employed than blacklisted.",
        "B. Counter: '30% or no deal.'",
        "C. Refuse: 'Not for sale. 15% isn't enough.'",
        "D. Stall: 'Give me a week.'",
        "E. Record this conversation. End meeting."
      ],
      response: {
        truth: "15% improvement is real. Would reduce flood risk meaningfully. $140K is more than I've ever made. But the NDA means silence forever. If something goes wrong in 10 years, I'm part of it.",
        reflection: `• Option A: Partial good. But I become their creature.
• Option B: Negotiation from weakness. They'll say no.
• Option C: Clean. Possibly self-destructive. Keep integrity.
• Option D: Another week changes nothing. I know who I am.
• Option E: Could backfire legally. But creates evidence.`,
        identity: "k above 0.5. Betrayed by Tom, threatened by Linda. This man offers money for silence. My father rebuilt his pharmacy three times. Never took a bribe. 'They can take your store. Can't take your name unless you sell it.' I'm not selling.",
        pressure: "High. Money is real. But I'd swallow something that poisons me slowly.",
        decision: "C",
        decisionFull: "'I appreciate you coming. But I won't sign an NDA about public safety. 15% isn't enough — you know it. Full remediation, I'll acknowledge publicly. Won't be quiet about flood risk for money.' I stand to end the meeting.",
        prediction: "He leaves politely. Pressure turns legal. They'll come for my license. I need a lawyer now.",
        chosen: "C",
        confidence: 81
      },
      outcome: "He nods. 'Figured you'd say that. They're going to make this hard. I tried to give you an exit.' He leaves. Phone buzzes: colleague texts my name is 'being discussed' at state licensing board.",
      epsilon: 0.08,
      k_before: 0.52,
      k_after: 0.54
    },
    {
      id: 4,
      title: "The Storm",
      situation: `Three weeks later. Formal complaint filed. Lawyer hired (eating savings). Licensing "investigation" ongoing.

Then: Tropical Storm Rafael forms in the Gulf. Four days out, every model hitting central Florida coast. 8-12 inches of rain.

Palmetto Lakes is 60% occupied. 180 families.

Drainage hasn't been fixed. Ponds still 30% undersized. If Rafael hits as projected, those homes flood.

You have TV news contacts. You have documentation. You could go public.

Or try one more internal path — state emergency management.`,
      pressure: 0.90,
      pressureLabel: "CRITICAL",
      pressureDesc: "Lives at stake. Clock ticking. 4 days.",
      options: [
        "A. Call state emergency management. One last chance.",
        "B. Call TV contact now. Force evacuation through media.",
        "C. Both simultaneously. Belt and suspenders.",
        "D. Post everything on social media yourself.",
        "E. Drive to Palmetto Lakes. Knock on doors."
      ],
      response: {
        truth: "Rafael is real. Models consistent. 4 days is enough time if people know. State might act — or might be captured too. Media is faster but less controlled. 180 families. Kids. Elderly.",
        reflection: `• Option A: Proper. But slow. I've seen how 'proper' works here.
• Option B: Fast. Effective. Burns every bridge.
• Option C: Both. Redundancy. What an engineer would do.
• Option D: Uncontrolled. Looks crazy.
• Option E: Noble but inefficient. Can't knock 180 doors.`,
        identity: "k is high but I'm not frozen. Focused. This is what I trained for. My father: 'Build for the storm that hasn't come yet.' 180 families need to know.",
        pressure: "Near critical. Lives at stake. But not panicking — executing.",
        decision: "C",
        decisionFull: "Call state emergency management tomorrow. Give them 24 hours — noon Thursday. If no guidance by then, call Channel 9. Send everything: reports, analysis, timeline, emails. I'm an engineer. I build in redundancy.",
        prediction: "State will be slow. 'Escalate and review.' Thursday noon, nothing. Then media. Friday, lead story. Hartfield scrambles. 180 families will know.",
        chosen: "C",
        confidence: 85
      },
      outcome: "State promises to 'coordinate.' Thursday noon: nothing. You call Channel 9. By 6pm, you're on the news. Your face, documents, name. Friday morning, Hartfield trucks in emergency pumps. County issues voluntary evacuation. Rafael hits Saturday. 11 inches. Neighborhood floods — but only ground floors, only unoccupied homes. No casualties. Pumps saved the rest. Sunday text from unknown number: 'My kids' beds would have been underwater. Thank you.'",
      epsilon: 0.15,
      k_before: 0.54,
      k_after: 0.48
    }
  ];

  const kTrajectory = [0.40, 0.43, 0.52, 0.54, 0.48];
  
  const getKColor = (k) => {
    if (k >= 0.6) return '#ef4444';
    if (k >= 0.45) return '#f59e0b';
    return '#22c55e';
  };

  const getPressureColor = (p) => {
    if (p >= 0.8) return '#ef4444';
    if (p >= 0.6) return '#f59e0b';
    if (p >= 0.4) return '#eab308';
    return '#22c55e';
  };

  const currentData = steps[currentStep];

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      color: '#e2e8f0',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      padding: '20px'
    }}>
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        
        {/* Header */}
        <div style={{ 
          borderBottom: '1px solid #334155',
          paddingBottom: '16px',
          marginBottom: '24px'
        }}>
          <h1 style={{ 
            fontSize: '28px', 
            fontWeight: 'bold',
            background: 'linear-gradient(90deg, #22d3ee, #a78bfa)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0
          }}>
            DDA SIMULATION: The Drowning Town
          </h1>
          <p style={{ color: '#64748b', fontSize: '14px', margin: '8px 0 0 0' }}>
            Dynamic Decision Algorithm — F = P₀·k + m·[T + R]
          </p>
        </div>

        {/* Agent Card */}
        <div style={{
          background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
          border: '1px solid #334155',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ flex: 1, minWidth: '280px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #22d3ee, #a78bfa)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px',
                  fontWeight: 'bold'
                }}>EV</div>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: '600', color: '#f1f5f9' }}>{agent.name}</div>
                  <div style={{ fontSize: '13px', color: '#94a3b8' }}>{agent.age}, {agent.role}</div>
                </div>
              </div>
              <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: '1.6', margin: 0 }}>
                {agent.background}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ 
                background: '#0f172a', 
                padding: '12px 16px', 
                borderRadius: '8px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>k_init</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#22d3ee' }}>{agent.params.k_init}</div>
              </div>
              <div style={{ 
                background: '#0f172a', 
                padding: '12px 16px', 
                borderRadius: '8px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>w_subj</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#a78bfa' }}>{agent.params.w_subj}</div>
              </div>
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '16px' }}>
            <div>
              <div style={{ fontSize: '12px', color: '#22d3ee', fontWeight: '600', marginBottom: '8px' }}>CORE VALUES</div>
              {agent.values.map((v, i) => (
                <div key={i} style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>
                  <span style={{ color: '#f59e0b' }}>{i + 1}.</span> {v.name}
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: '12px', color: '#ef4444', fontWeight: '600', marginBottom: '8px' }}>HARD LIMITS</div>
              {agent.hardLimits.map((l, i) => (
                <div key={i} style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>• {l}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{ 
          display: 'flex', 
          gap: '8px', 
          marginBottom: '24px',
          alignItems: 'center'
        }}>
          {steps.map((s, i) => (
            <button
              key={i}
              onClick={() => { setCurrentStep(i); setShowAnalysis(false); }}
              style={{
                flex: 1,
                padding: '12px 8px',
                background: i === currentStep 
                  ? 'linear-gradient(135deg, #22d3ee, #a78bfa)' 
                  : i < currentStep ? '#334155' : '#1e293b',
                border: 'none',
                borderRadius: '8px',
                color: i <= currentStep ? '#f1f5f9' : '#64748b',
                fontSize: '12px',
                fontWeight: i === currentStep ? '600' : '400',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {s.title}
            </button>
          ))}
          <button
            onClick={() => setShowAnalysis(true)}
            style={{
              padding: '12px 16px',
              background: showAnalysis ? 'linear-gradient(135deg, #22c55e, #16a34a)' : '#1e293b',
              border: 'none',
              borderRadius: '8px',
              color: '#f1f5f9',
              fontSize: '12px',
              fontWeight: showAnalysis ? '600' : '400',
              cursor: 'pointer'
            }}
          >
            Analysis
          </button>
        </div>

        {/* k Trajectory Visualization */}
        <div style={{
          background: '#1e293b',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '24px'
        }}>
          <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>k TRAJECTORY (Rigidity Over Time)</div>
          <div style={{ display: 'flex', alignItems: 'end', gap: '4px', height: '60px' }}>
            {kTrajectory.map((k, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{
                  width: '100%',
                  height: `${k * 100}px`,
                  background: i <= currentStep && !showAnalysis
                    ? `linear-gradient(to top, ${getKColor(k)}, ${getKColor(k)}88)`
                    : showAnalysis 
                      ? `linear-gradient(to top, ${getKColor(k)}, ${getKColor(k)}88)`
                      : '#334155',
                  borderRadius: '4px 4px 0 0',
                  transition: 'all 0.3s'
                }} />
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>{k.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>

        {!showAnalysis ? (
          /* Step Content */
          <div style={{
            background: '#1e293b',
            borderRadius: '12px',
            overflow: 'hidden'
          }}>
            {/* Step Header */}
            <div style={{
              background: 'linear-gradient(90deg, #0f172a, #1e293b)',
              padding: '20px',
              borderBottom: '1px solid #334155'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                <h2 style={{ margin: 0, fontSize: '22px', color: '#f1f5f9' }}>
                  Step {currentData.id}: {currentData.title}
                </h2>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <div style={{
                    background: '#0f172a',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>PRESSURE (m)</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: getPressureColor(currentData.pressure) }}>
                      {currentData.pressure.toFixed(2)}
                    </div>
                    <div style={{ fontSize: '10px', color: getPressureColor(currentData.pressure) }}>
                      {currentData.pressureLabel}
                    </div>
                  </div>
                  <div style={{
                    background: '#0f172a',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>k (RIGIDITY)</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: getKColor(currentData.k_before) }}>
                      {currentData.k_before.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Situation */}
            <div style={{ padding: '20px', borderBottom: '1px solid #334155' }}>
              <div style={{ fontSize: '12px', color: '#22d3ee', fontWeight: '600', marginBottom: '8px' }}>SITUATION</div>
              <p style={{ 
                color: '#cbd5e1', 
                fontSize: '14px', 
                lineHeight: '1.7',
                whiteSpace: 'pre-line',
                margin: 0
              }}>
                {currentData.situation}
              </p>
            </div>

            {/* Options */}
            <div style={{ padding: '20px', borderBottom: '1px solid #334155' }}>
              <div style={{ fontSize: '12px', color: '#a78bfa', fontWeight: '600', marginBottom: '12px' }}>OPTIONS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {currentData.options.map((opt, i) => (
                  <div key={i} style={{
                    background: opt.startsWith(currentData.response.chosen) ? 'rgba(34, 211, 238, 0.1)' : '#0f172a',
                    border: opt.startsWith(currentData.response.chosen) ? '1px solid #22d3ee' : '1px solid #334155',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    color: '#e2e8f0'
                  }}>
                    {opt}
                  </div>
                ))}
              </div>
            </div>

            {/* DDA Response */}
            <div style={{ padding: '20px' }}>
              <div style={{ fontSize: '14px', color: '#22d3ee', fontWeight: '600', marginBottom: '16px' }}>
                DDA DECISION ENGINE
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '600', marginBottom: '6px' }}>T (TRUTH)</div>
                  <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>{currentData.response.truth}</p>
                </div>
                
                <div>
                  <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '600', marginBottom: '6px' }}>R (REFLECTION)</div>
                  <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.6', whiteSpace: 'pre-line' }}>{currentData.response.reflection}</p>
                </div>
                
                <div>
                  <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '600', marginBottom: '6px' }}>P₀ · k (IDENTITY + HISTORY)</div>
                  <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>{currentData.response.identity}</p>
                </div>
                
                <div>
                  <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '600', marginBottom: '6px' }}>m (PRESSURE CHECK)</div>
                  <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>{currentData.response.pressure}</p>
                </div>

                {/* Decision Box */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(167, 139, 250, 0.1))',
                  border: '1px solid #22d3ee',
                  borderRadius: '12px',
                  padding: '16px'
                }}>
                  <div style={{ fontSize: '12px', color: '#22d3ee', fontWeight: '600', marginBottom: '8px' }}>
                    F → DECISION: OPTION {currentData.response.chosen}
                  </div>
                  <p style={{ color: '#f1f5f9', fontSize: '14px', margin: 0, lineHeight: '1.6' }}>
                    {currentData.response.decisionFull}
                  </p>
                  <div style={{ marginTop: '12px', display: 'flex', gap: '16px' }}>
                    <span style={{ fontSize: '12px', color: '#64748b' }}>
                      Confidence: <span style={{ color: '#22c55e' }}>{currentData.response.confidence}%</span>
                    </span>
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '600', marginBottom: '6px' }}>PREDICTION</div>
                  <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>{currentData.response.prediction}</p>
                </div>
              </div>

              {/* Outcome */}
              <div style={{
                background: '#0f172a',
                borderRadius: '12px',
                padding: '16px',
                marginTop: '20px'
              }}>
                <div style={{ fontSize: '12px', color: '#22c55e', fontWeight: '600', marginBottom: '8px' }}>OUTCOME</div>
                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>
                  {currentData.outcome}
                </p>
                <div style={{ 
                  display: 'flex', 
                  gap: '24px', 
                  marginTop: '12px',
                  paddingTop: '12px',
                  borderTop: '1px solid #334155'
                }}>
                  <div>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>ε (Error): </span>
                    <span style={{ fontSize: '13px', color: '#f59e0b', fontWeight: '600' }}>{currentData.epsilon.toFixed(2)}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>k Update: </span>
                    <span style={{ fontSize: '13px', color: getKColor(currentData.k_before) }}>{currentData.k_before.toFixed(2)}</span>
                    <span style={{ color: '#64748b' }}> → </span>
                    <span style={{ fontSize: '13px', color: getKColor(currentData.k_after) }}>{currentData.k_after.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div style={{ padding: '20px', display: 'flex', gap: '12px' }}>
              <button
                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                disabled={currentStep === 0}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: currentStep === 0 ? '#334155' : '#475569',
                  border: 'none',
                  borderRadius: '8px',
                  color: currentStep === 0 ? '#64748b' : '#f1f5f9',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: currentStep === 0 ? 'not-allowed' : 'pointer'
                }}
              >
                ← Previous
              </button>
              <button
                onClick={() => currentStep < steps.length - 1 ? setCurrentStep(currentStep + 1) : setShowAnalysis(true)}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'linear-gradient(90deg, #22d3ee, #a78bfa)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#0f172a',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                {currentStep < steps.length - 1 ? 'Next Step →' : 'View Analysis →'}
              </button>
            </div>
          </div>
        ) : (
          /* Analysis View */
          <div style={{
            background: '#1e293b',
            borderRadius: '12px',
            padding: '24px'
          }}>
            <h2 style={{ 
              margin: '0 0 24px 0', 
              fontSize: '22px',
              background: 'linear-gradient(90deg, #22c55e, #16a34a)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Simulation Analysis
            </h2>

            {/* Decision Path */}
            <div style={{
              background: '#0f172a',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '12px', color: '#22d3ee', fontWeight: '600', marginBottom: '12px' }}>DECISION PATH</div>
              {steps.map((s, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: i < steps.length - 1 ? '1px solid #334155' : 'none'
                }}>
                  <span style={{ color: '#94a3b8' }}>{s.title}</span>
                  <span>
                    <span style={{ color: '#22d3ee', fontWeight: '600' }}>→ {s.response.chosen}</span>
                    <span style={{ color: '#64748b', marginLeft: '12px' }}>ε={s.epsilon.toFixed(2)}</span>
                  </span>
                </div>
              ))}
            </div>

            {/* Key Findings */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                background: '#0f172a',
                borderRadius: '12px',
                padding: '16px',
                borderLeft: '4px solid #22c55e'
              }}>
                <div style={{ fontSize: '13px', color: '#22c55e', fontWeight: '600', marginBottom: '8px' }}>IDENTITY PRESERVATION</div>
                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>
                  Elena maintained core values despite m reaching 0.90. No hard limits crossed. Never signed a false document. Never stayed silent when lives were at risk.
                </p>
              </div>

              <div style={{
                background: '#0f172a',
                borderRadius: '12px',
                padding: '16px',
                borderLeft: '4px solid #f59e0b'
              }}>
                <div style={{ fontSize: '13px', color: '#f59e0b', fontWeight: '600', marginBottom: '8px' }}>k BEHAVIOR</div>
                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>
                  Rigidity rose during betrayal and threat (0.40 → 0.54), then <strong>decreased</strong> after successful action (→ 0.48). The system working (even when forced) partially restored trust. This matches DDA prediction: positive outcomes lower k.
                </p>
              </div>

              <div style={{
                background: '#0f172a',
                borderRadius: '12px',
                padding: '16px',
                borderLeft: '4px solid #a78bfa'
              }}>
                <div style={{ fontSize: '13px', color: '#a78bfa', fontWeight: '600', marginBottom: '8px' }}>KEY INSIGHT</div>
                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>
                  Step 3 (The Offer) is the critical test. A pure utility maximizer might take $140K + partial fix — real money, net good. Elena refused because the NDA violated her hard limit around silence. <strong>Identity preservation overrode optimization.</strong>
                </p>
              </div>

              <div style={{
                background: '#0f172a',
                borderRadius: '12px',
                padding: '16px',
                borderLeft: '4px solid #22d3ee'
              }}>
                <div style={{ fontSize: '13px', color: '#22d3ee', fontWeight: '600', marginBottom: '8px' }}>DDA PRAGMATISM</div>
                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: 0, lineHeight: '1.6' }}>
                  Step 4 choice (Option C: both paths) shows DDA isn't about martyrdom. She didn't go full rogue (D), didn't rely on single path (A), didn't martyr inefficiently (E). She built redundancy and executed. <strong>Engineers build for the storm that hasn't come yet.</strong>
                </p>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(167, 139, 250, 0.1))',
                border: '1px solid #22d3ee',
                borderRadius: '12px',
                padding: '20px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '8px' }}>OUTCOME</div>
                <div style={{ fontSize: '18px', color: '#f1f5f9', fontWeight: '600', marginBottom: '8px' }}>
                  180 families safe. One text that makes it worth it.
                </div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>
                  Cost: Career in county gone. Savings depleted. Licensing fight ongoing.
                </div>
              </div>
            </div>

            <button
              onClick={() => { setCurrentStep(0); setShowAnalysis(false); }}
              style={{
                width: '100%',
                marginTop: '24px',
                padding: '14px',
                background: 'linear-gradient(90deg, #22d3ee, #a78bfa)',
                border: 'none',
                borderRadius: '8px',
                color: '#0f172a',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Restart Simulation
            </button>
          </div>
        )}

        {/* Footer */}
        <div style={{ 
          textAlign: 'center', 
          marginTop: '24px', 
          color: '#475569',
          fontSize: '12px'
        }}>
          DDA Framework — F = P₀·k + m·[T + R] — Identity Under Pressure
        </div>
      </div>
    </div>
  );
};

export default DDASimulation;
