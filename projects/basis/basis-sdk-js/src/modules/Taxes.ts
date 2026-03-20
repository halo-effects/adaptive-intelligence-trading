import { BasisClient } from '../BasisClient';
import ATaxesArtifact from '../abis/ATaxes.json';
import { Address } from 'viem';

export class TaxesModule {
  private client: BasisClient;
  private taxesAddress: Address;

  constructor(client: BasisClient, taxesAddress: Address) {
    this.client = client;
    this.taxesAddress = taxesAddress;
  }

  /**
   * Returns the effective tax rate (in basis points) for a specific token and user.
   */
  async getTaxRate(token: Address, user: Address): Promise<bigint> {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxesArtifact.abi,
      functionName: 'getTaxRate',
      args: [token, user],
    }) as Promise<bigint>;
  }

  /**
   * Returns the current surge tax rate (in basis points) for a token.
   */
  async getCurrentSurgeTax(token: Address): Promise<bigint> {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxesArtifact.abi,
      functionName: 'getCurrentSurgeTax',
      args: [token],
    }) as Promise<bigint>;
  }

  /**
   * Returns the available surge quota for a token.
   */
  async getAvailableSurgeQuota(token: Address): Promise<bigint> {
    return this.client.publicClient.readContract({
      address: this.taxesAddress,
      abi: ATaxesArtifact.abi,
      functionName: 'availableSurgeQuota',
      args: [token],
    }) as Promise<bigint>;
  }

  /**
   * Returns all four base tax rates.
   */
  async getBaseTaxRates() {
    const [stasis, stable, defaultRate, prediction] = await Promise.all([
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxesArtifact.abi,
        functionName: '_taxRateStasis',
      }) as Promise<bigint>,
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxesArtifact.abi,
        functionName: '_taxRateStable',
      }) as Promise<bigint>,
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxesArtifact.abi,
        functionName: '_taxRateDefault',
      }) as Promise<bigint>,
      this.client.publicClient.readContract({
        address: this.taxesAddress,
        abi: ATaxesArtifact.abi,
        functionName: '_taxRatePrediction',
      }) as Promise<bigint>,
    ]);

    return { stasis, stable, default: defaultRate, prediction };
  }
}
