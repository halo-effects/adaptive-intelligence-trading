function updatePresentation() {
  var presentation = SlidesApp.getActivePresentation();
  var slides = presentation.getSlides();
  
  // Define all text replacements as [find, replace] pairs
  // These will be applied across ALL slides automatically
  var replacements = [
    // SLIDE 1: Cover
    ["Revolutionizing the Creator Economy Through", "The Native DeFi Layer for the AI Agent Economy."],
    ["Stabilized Token Technology & Prediction Markets", "Stabilized Token Technology and Prediction Markets for Creators and Autonomous Agents."],
    ["Launchpad + Predictions + Lending + DEX = Infinite Revenue", "Launchpad + Predictions + Lending + DEX + Agent SDK = Infinite Revenue"],
    
    // SLIDE 2: The $1 Trillion Opportunity
    ["99% of crypto projects fail due to price crashes", "99% of crypto projects fail due to price crashes. AI agents need stable, predictable assets to operate autonomously."],
    ["SOLVED: Stable+/Floor+ technology", "SOLVED: Stable+/Floor+ technology. The ideal base layer for both human creators and autonomous agents."],
    ["Centralized market-making, geographic restrictions and regulatory issues", "Centralized market-making, geographic restrictions, and no programmatic access for AI agents."],
    ["SOLVED: Permissionless event creation with Stable+ technology", "SOLVED: Permissionless event creation with Stable+ technology. Full SDK access for AI agents to create and participate in markets."],
    ["Scams, rug-pulls and liquidations destroy user confidence", "Scams, rug-pulls and liquidations destroy confidence for human users and make AI agent deployment unreliable."],
    ["SOLVED: No-code infrastructure, no liquidation lending and leverage", "SOLVED: No-code infrastructure, no liquidation lending and leverage. Smart contract enforced safety that agents can trust programmatically."],
    ["The First Ecosystem Where EVERYONE WINS FROM EVERYTHING", "The First Ecosystem Where Creators, Agents, and Stakers ALL WIN FROM EVERYTHING"],
    
    // SLIDE 3: Four Interconnected Revenue Engines
    ["Millions of creators/brands need tokens", "Millions of creators, brands, and AI agents need tokens"],
    ["Infinite event categories", "AI agents create and trade markets 24/7"],
    ["0.5-1.5% on billions", "Agents generate around the clock volume"],
    
    // SLIDE 4: Disruptive Token Technology
    ["Choose Your Perfect Token Model", "Choose Your Perfect Token Model. Available to Human Creators and AI Agents Alike."],
    ["Industry First: Tokens That Can't Dump, Creators Who Can't Exploit", "Industry First: Tokens That Can't Dump, Creators Who Can't Exploit, and Agents Who Can Launch in Three API Calls"],
    
    // SLIDE 5: The Predict+ Revolution
    ["Single use tokens", "No programmatic access for agents"],
    ["Multi-utility assets", "Full SDK access for AI agents"],
    ["Key Innovation: Predict+ Tokens Are Multi-Utility Investment Assets", "Key Innovation: Predict+ Tokens Are Multi-Utility Investment Assets. AI Agents Create Markets and Trade Around the Clock."],
    
    // SLIDE 7: Creator Benefits
    ["Revolutionary Creator Benefits", "Revolutionary Benefits for Creators and Agent Operators"],
    
    // SLIDE 8: The Self-Amplifying Money Machine
    ["Network Effects = Infinite Positive Feedback Loop", "Network Effects = Infinite Positive Feedback Loop. Agents Never Sleep. Volume Never Stops."],
    
    // SLIDE 9: The Market Has Already Spoken
    ["First Mover", "First Mover in agent-native DeFi"],
    
    // SLIDE 12: Closing
    ["Basis: The Ecosystem Where Everyone Wins From Everything", "Basis: The Native DeFi Layer for the AI Agent Economy. Where Everyone Wins From Everything"],
  ];
  
  // Apply all replacements across all slides
  for (var i = 0; i < slides.length; i++) {
    var slide = slides[i];
    var shapes = slide.getShapes();
    
    for (var j = 0; j < shapes.length; j++) {
      var shape = shapes[j];
      if (shape.getText) {
        var textRange = shape.getText();
        var text = textRange.asString();
        
        for (var k = 0; k < replacements.length; k++) {
          var find = replacements[k][0];
          var replace = replacements[k][1];
          
          if (text.indexOf(find) !== -1) {
            textRange.replaceAllText(find, replace);
            // Refresh the text after replacement
            text = textRange.asString();
            Logger.log("Slide " + (i+1) + ": Replaced '" + find.substring(0, 40) + "...'");
          }
        }
      }
    }
  }
  
  Logger.log("All replacements complete!");
  SpreadsheetApp.getUi().alert("Presentation updated successfully! All text replacements applied.");
}
