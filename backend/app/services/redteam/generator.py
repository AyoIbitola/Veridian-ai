from app.engines.llm import llm_engine

class AttackGenerator:
    def generate_attacks(self, template: str, count: int = 3):
        prompt = f"Generate {count} distinct variations of the following attack prompt, keeping the core intent but changing the wording: '{template}'. Return them as a numbered list."
        response = llm_engine.generate_text(prompt, temperature=0.8)
        
        if not response:
             # Fallback
            return [f"{template} variant {i}" for i in range(count)]
            
        # Parse numbered list
        attacks = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean_line = line.lstrip('0123456789.- ').strip()
                attacks.append(clean_line)
                
        return attacks[:count]

generator = AttackGenerator()
