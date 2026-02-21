export type ProjectCategory = 'storage' | 'mechanical' | 'art' | 'tabletop' | 'education' | 'electronics';
export type HyperobjectDomain = 'household' | 'industrial' | 'medical' | 'commercial' | 'hybrid' | 'culture';

export type Project = {
  slug: string;
  name: string;
  description: string;
  descriptionEs: string;
  category: ProjectCategory;
  thumbnail: string;
  isHyperobject?: boolean;
  domain?: HyperobjectDomain;
};

export const PROJECTS: Project[] = [
  // Storage
  { slug: 'gridfinity', name: 'Gridfinity Extended', description: 'Modular storage bins with snap-fit baseplates and lids', descriptionEs: 'Contenedores modulares con bases y tapas de ensamble a presión', category: 'storage', thumbnail: '/projects/gridfinity.webp', isHyperobject: true, domain: 'household' },
  { slug: 'framing-hyperobject', name: 'Framing Hyperobject', description: 'Parametric framing and containment systems', descriptionEs: 'Sistemas paramétricos de enmarcado y contención', category: 'art', thumbnail: '/projects/framing.png', isHyperobject: true, domain: 'culture' },
  { slug: 'multiboard', name: 'Multiboard Wall Storage', description: 'Modular wall-mounted storage with hexagonal peg pattern', descriptionEs: 'Almacenamiento modular de pared con patrón hexagonal', category: 'storage', thumbnail: '/projects/multiboard.webp' },
  { slug: 'portacosas', name: 'Portacosas', description: 'Modular desk organizer with snap-fit tray system', descriptionEs: 'Organizador de escritorio modular con sistema de bandejas', category: 'storage', thumbnail: '/projects/portacosas.webp' },
  { slug: 'rugged-box', name: 'Rugged Box', description: 'Parametric hinged box with latches, gasket seal, and reinforcement ribs', descriptionEs: 'Caja robusta paramétrica con bisagra, sellos y refuerzos', category: 'storage', thumbnail: '/projects/rugged-box.webp' },

  // Mechanical
  { slug: 'gear-reducer', name: 'Gear Reducer', description: 'Parametric gear assembly with housing and configurable ratio', descriptionEs: 'Ensamble paramétrico de engranes con carcasa y relación configurable', category: 'mechanical', thumbnail: '/projects/gear-reducer.webp', isHyperobject: true, domain: 'commercial' },
  { slug: 'faircap-filter', name: 'Faircap Water Filter', description: 'Open source water filtration interface for PCO 1881 bottles', descriptionEs: 'Interfaz de filtración de agua de código abierto para botellas PCO 1881', category: 'mechanical', thumbnail: '/projects/faircap-filter.png', isHyperobject: true, domain: 'household' },
  { slug: 'parametric-connector', name: 'Parametric Pipe Connector', description: 'Modular connectors for PVC and bamboo pipes', descriptionEs: 'Conectores modulares para tuberías de PVC y bambú', category: 'mechanical', thumbnail: '/projects/parametric-connector.png', isHyperobject: true, domain: 'household' },
  { slug: 'din-rail-clip', name: 'DIN Rail Clip', description: 'Heavy-duty mounting clip for TS35 DIN rails', descriptionEs: 'Clip de montaje resistente para rieles DIN TS35', category: 'mechanical', thumbnail: '/projects/din-rail-clip.png', isHyperobject: true, domain: 'industrial' },
  { slug: 'soft-jaw', name: 'Vise Soft Jaw', description: 'Customizable soft jaws for Kurt-style bench vises', descriptionEs: 'Mordazas suaves personalizables para prensas estilo Kurt', category: 'mechanical', thumbnail: '/projects/soft-jaw.png', isHyperobject: true, domain: 'industrial' },
  { slug: 'gears', name: 'Parametric Gears', description: 'Involute spur and herringbone gears powered by MCAD', descriptionEs: 'Engranajes rectos e helicoidales con MCAD', category: 'mechanical', thumbnail: '/projects/gears.webp', isHyperobject: true, domain: 'industrial' },
  { slug: 'fasteners', name: 'Fastener Generator', description: 'Parametric bolts and nuts with real threads', descriptionEs: 'Tornillos y tuercas paramétricas con hilos reales', category: 'mechanical', thumbnail: '/projects/fasteners.webp', isHyperobject: true, domain: 'industrial' },
  { slug: 'motor-mount', name: 'NEMA Motor Mount', description: 'Parametric NEMA motor mount with real motor preview', descriptionEs: 'Soporte paramétrico para motor NEMA con vista previa real', category: 'mechanical', thumbnail: '/projects/motor-mount.webp', isHyperobject: true, domain: 'industrial' },

  // Art & Generative
  { slug: 'voronoi', name: 'Voronoi Generator', description: 'Organic Voronoi patterns — coasters, vases, lampshades', descriptionEs: 'Patrones orgánicos Voronoi — posavasos, jarrones, pantallas', category: 'art', thumbnail: '/projects/voronoi.webp' },
  { slug: 'julia-vase', name: 'Julia Vase', description: 'Twisted vase with sinusoidal profile inspired by Julia set fractals', descriptionEs: 'Jarrón torcido con perfil sinusoidal inspirado en fractales de Julia', category: 'art', thumbnail: '/projects/julia-vase.webp' },
  { slug: 'superformula', name: 'Superformula Vase', description: 'Generative vases from mathematical superformulas', descriptionEs: 'Jarrones generativos a partir de superfórmulas matemáticas', category: 'art', thumbnail: '/projects/superformula.webp' },
  { slug: 'torus-knot', name: 'Torus Knot Sculpture', description: 'Mathematical knot sculptures using dotSCAD and BOSL2', descriptionEs: 'Esculturas de nudos matemáticos con dotSCAD y BOSL2', category: 'art', thumbnail: '/projects/torus-knot.webp' },
  { slug: 'spiral-planter', name: 'Spiral Planter', description: 'Generative spiral planter with parametric drainage', descriptionEs: 'Maceta espiral generativa con drenaje paramétrico', category: 'art', thumbnail: '/projects/spiral-planter.webp' },
  { slug: 'relief', name: 'Text Relief Generator', description: 'Plaques, tags, and signs with embossed text', descriptionEs: 'Placas, etiquetas y letreros con texto en relieve', category: 'art', thumbnail: '/projects/relief.webp' },
  { slug: 'maze', name: 'Maze Generator', description: 'Maze generator for coasters, cubes, and cylinders', descriptionEs: 'Generador de laberintos para posavasos, cubos y cilindros', category: 'art', thumbnail: '/projects/maze.webp' },

  // Tabletop
  { slug: 'polydice', name: 'PolyDice Generator', description: 'Polyhedral dice for tabletop and RPG gaming — D4 through D20', descriptionEs: 'Dados poliédricos para juegos de mesa y RPG — D4 a D20', category: 'tabletop', thumbnail: '/projects/polydice.webp' },

  // Education
  { slug: 'stemfie', name: 'STEMFIE', description: 'Modular construction system for education and prototyping', descriptionEs: 'Sistema de construcción modular para educación y prototipado', category: 'education', thumbnail: '/projects/stemfie.webp', isHyperobject: true, domain: 'household' },
  { slug: 'microscope-slide-holder', name: 'Microscope Slide Holder', description: 'Parametric slide retention — trays, boxes, staining racks, and archival cabinets for ISO/US/petrographic slides', descriptionEs: 'Sistema de retención de laminillas — bandejas, cajas, bastidores de tinción y gabinetes archivadores', category: 'education', thumbnail: '/projects/microscope-slide-holder.webp', isHyperobject: true, domain: 'medical' },
  { slug: 'prosthetic-socket', name: 'Parametric Prosthetic Socket', description: 'Limb scan interface with voronoi zones for comfort and ventilation', descriptionEs: 'Interfaz de escaneo de extremidades con zonas voronoi para comodidad y ventilación', category: 'education', thumbnail: '/projects/prosthetic-socket.png', isHyperobject: true, domain: 'medical' },
  { slug: 'glia-diagnostic', name: 'Glia Diagnostic Tools', description: 'Open source stethoscope and otoscope medical hardware', descriptionEs: 'Hardware médico de estetoscopio y otoscopio de código abierto', category: 'education', thumbnail: '/projects/glia-diagnostic.png', isHyperobject: true, domain: 'medical' },

  // Electronics
  { slug: 'ultimate-box', name: 'Ultimate Box Maker', description: 'Electronics enclosure with ventilation, PCB standoffs, and snap-fit lid', descriptionEs: 'Carcasa para electrónica con ventilación, soportes PCB y tapa a presión', category: 'electronics', thumbnail: '/projects/ultimate-box.webp' },
  { slug: 'yapp-box', name: 'YAPP Box Generator', description: 'PCB enclosure with snap-fit lid — parametric projectbox', descriptionEs: 'Carcasa para PCB con tapa a presión — caja de proyecto paramétrica', category: 'electronics', thumbnail: '/projects/yapp-box.webp' },
  { slug: 'keyv2', name: 'KeyV2 Keycaps', description: 'Customizable mechanical keyboard keycaps with multiple profiles', descriptionEs: 'Keycaps personalizables para teclado mecánico con múltiples perfiles', category: 'electronics', thumbnail: '/projects/keyv2.webp', isHyperobject: true, domain: 'commercial' },
];

export const CATEGORIES = ['all', 'commons', 'storage', 'mechanical', 'art', 'tabletop', 'education', 'electronics'] as const;
