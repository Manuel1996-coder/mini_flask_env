declare module '@shopify/polaris' {
  export interface TextProps {
    variant?: string;
    fontWeight?: string;
    color?: string;
    children?: React.ReactNode;
  }

  export interface CardProps {
    sectioned?: boolean;
    title?: string;
    children?: React.ReactNode;
  }

  export interface SpinnerProps {
    accessibilityLabel?: string;
    size?: 'small' | 'large';
  }

  export interface ButtonProps {
    onClick?: () => void;
    primary?: boolean;
    size?: 'slim' | 'medium' | 'large';
    children?: React.ReactNode;
  }

  export interface DataTableProps {
    columnContentTypes: string[];
    headings: React.ReactNode[];
    rows: any[][];
  }

  export interface BadgeProps {
    status?: 'success' | 'warning' | 'info' | 'attention';
    children?: React.ReactNode;
  }

  export const Card: React.FC<CardProps>;
  export const Text: React.FC<TextProps>;
  export const Spinner: React.FC<SpinnerProps>;
  export const Button: React.FC<ButtonProps>;
  export const DataTable: React.FC<DataTableProps>;
  export const Badge: React.FC<BadgeProps>;
}

declare module '@shopify/app-bridge-react' {
  export interface TitleBarProps {
    title: string;
  }

  export interface ToastProps {
    content: string;
    error?: boolean;
    onDismiss: () => void;
  }

  export interface NavigationMenuProps {
    navigationLinks: Array<{
      label: string;
      destination: string;
    }>;
  }

  export const TitleBar: React.FC<TitleBarProps>;
  export const Toast: React.FC<ToastProps>;
  export const NavigationMenu: React.FC<NavigationMenuProps>;
  export const useAppBridge: () => any;
  export const AppProvider: React.FC<{
    config: {
      apiKey: string;
      host: string;
      forceRedirect: boolean;
    };
    children: React.ReactNode;
  }>;
}

declare module '@shopify/app-bridge-utils' {
  export const authenticatedFetch: (app: any) => (url: string, options?: RequestInit) => Promise<Response>;
}

declare module '@emotion/styled' {
  import { CreateStyled } from '@emotion/styled/types';
  
  const styled: CreateStyled;
  export default styled;
}

declare module '@emotion/react' {
  export const ThemeProvider: React.FC<{
    theme: any;
    children: React.ReactNode;
  }>;
} 