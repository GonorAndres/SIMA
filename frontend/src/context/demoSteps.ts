export interface DemoStep {
  path: string;
  scrollTo?: string;
  narrativeKey: string;
}

const demoSteps: DemoStep[] = [
  { path: '/', scrollTo: 'hero', narrativeKey: 'demo.step1' },
  { path: '/mortalidad', scrollTo: 'graduation', narrativeKey: 'demo.step2' },
  { path: '/mortalidad', scrollTo: 'surface', narrativeKey: 'demo.step3' },
  { path: '/mortalidad', scrollTo: 'lee-carter', narrativeKey: 'demo.step4' },
  { path: '/mortalidad', scrollTo: 'projection', narrativeKey: 'demo.step5' },
  { path: '/mortalidad', scrollTo: 'validation', narrativeKey: 'demo.step6' },
  { path: '/tarificacion', scrollTo: 'top', narrativeKey: 'demo.step7' },
  { path: '/scr', scrollTo: 'top', narrativeKey: 'demo.step8' },
  { path: '/sensibilidad', scrollTo: 'interest', narrativeKey: 'demo.step9' },
  { path: '/sensibilidad', scrollTo: 'cross-country', narrativeKey: 'demo.step10' },
  { path: '/sensibilidad', scrollTo: 'covid', narrativeKey: 'demo.step11' },
  { path: '/metodologia', scrollTo: 'top', narrativeKey: 'demo.step12' },
];

export default demoSteps;
