/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone", // pra Dockerfile multi-stage enxuto
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "static-images.ifood.com.br" },
    ],
  },
};

export default nextConfig;
