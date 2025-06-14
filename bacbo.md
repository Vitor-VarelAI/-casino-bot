# 📑 Instruções (sem código) + Resumo do Jogo **Bac Bo**  

## 1. Resumo rápido do Bac Bo
- **Origem & Conceito:** Bac Bo é um jogo live da Evolution Gaming que combina a estrutura de apostas do Baccarat (Player, Banker, Tie) com dados em vez de cartas.  
- **Mecânica:** Dois dados para o Player e dois para o Banker são lançados em sequência; somam-se os valores de cada par. Quem tiver a soma mais alta vence.  
- **Apostas & Pagamentos:**  
  - **Player** ou **Banker** pagam 1 : 1.  
  - **Tie** tem pagamentos maiores e escalonados (p.ex. 88 : 1 se ambos somam 2 ou 12), mas casa com margem maior.  
- **RTP:** ≈ 98,87 % (semelhante ao Baccarat).  
- **Estratégia Recomendada:** Focar em Player ou Banker; evitar Tie. Martingale é possível, mas aumenta risco de banca quebrar.  

---

## 2. Integração no Bot existente

### 2.1 Visão Geral
| Item                    | O que fazer                                                   |
|-------------------------|---------------------------------------------------------------|
| **Novo comando**        | Criar `/bacbo` (e opcional `/bacbo_martingale`).              |
| **Menu inicial**        | Actualizar `/start` com botão “🎲 Bac Bo”.                    |
| **Fluxo de jogo**       | Utilizador escolhe Player ou Banker → bot mostra lançamento faseado → exibe resultado. |
| **Histórico**           | Guardar resultados por utilizador para métricas e ranking.    |
| **Premium**             | Desbloqueia estratégias avançadas, alertas e estatísticas extra. |
| **Mensagens agendadas** | Enviar felicitações semanais/mensais aos utilizadores com maior taxa de acerto. |
| **Logs & Analytics**    | Contar total de utilizadores, Premium, e jogadas Bac Bo.      |
| **Idiomas**             | Preparar estrutura multilíngua (PT-PT primeiro).             |

### 2.2 Passos por Prioridade
1. **Criar handlers/ficheiros** dedicados a Bac Bo (simulação, fluxo, Martingale opcional).  
2. **Actualizar menu `/start`** para incluir Bac Bo e manter Martingale atual.  
3. **Persistência**: expandir `user_data` para guardar histórico Bac Bo e flag Premium única.  
4. **Agendador**: configurar “Job Queue” para mensagens de ranking (semanal/mensal).  
5. **Painel Interno**: mostrar contagem de utilizadores e Premium, top jogadores.  
6. **README**: documentar novos comandos, funcionalidades e requisitos.  
7. **Deploy**: garantir requirements atualizados e testar flow end-to-end.

---

## 3. Considerações Importantes
- **Responsabilidade/Jogo Responsável:** incluir nota contra vício e lembrar limites.  
- **Empate (Tie):** tratar como resultado neutro no Martingale (repetir aposta) ou metade-perda, consoante definição de produto.  
- **Escalabilidade futura:** estrutura modular para adicionar mais jogos sem refatorar núcleo.  
- **UI/UX Telegram:** usar botões inline para navegação por etapas, evitando paredes de texto.  
- **Multilíngua:** isolar strings em ficheiros de tradução desde início para facilitar expansão.

---

### Próximo passo
Quando o dev receber estas instruções, deve:
1. Criar a pasta/módulo Bac Bo.  
2. Implementar o fluxo básico de jogo e menu.  
3. Fazer testes unitários na lógica de “quem ganha” e na progressão Martingale adaptada.  

Depois disso, validar com PM e avançar para funcionalidades Premium e agendamento.
