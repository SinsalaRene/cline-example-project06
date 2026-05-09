/**
 * Network Service Unit Tests
 *
 * Tests for the NetworkService API layer.
 * Tests cover topology fetching, CRUD operations for VNets, subnets, NSGs,
 * external devices, and network connections.
 */

import { TestBed } from '@angular/core/testing';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { NetworkService } from './network.service';
import {
    TopologyGraph,
    VirtualNetwork,
    Subnet,
    NetworkSecurityGroup,
    ExternalNetworkDevice,
    NetworkConnection,
    ConnectionType,
    DeviceType,
    NodeType,
    SyncStatus,
} from '../models/network.model';

describe('NetworkService', () => {
    let service: NetworkService;
    let httpController: any;

    const mockTopology: TopologyGraph = {
        nodes: [
            {
                id: 'vnet-1',
                type: NodeType.VIRTUAL_NETWORK,
                data: {
                    id: 'vnet-1',
                    name: 'vnet-production',
                    addressSpace: '10.0.0.0/16',
                    location: 'eastus',
                    resourceGroup: 'rg-production',
                } as VirtualNetwork,
                connections: [],
            },
        ],
        edges: [],
    };

    const mockVnet: VirtualNetwork = {
        id: 'vnet-1',
        name: 'vnet-production',
        addressSpace: '10.0.0.0/16',
        location: 'eastus',
        resourceGroup: 'rg-production',
    };

    beforeEach(() => {
        httpController = {
            get: jasmine.createSpy('get').and.returnValue(of(mockTopology)),
            post: jasmine.createSpy('post').and.returnValue(of(mockVnet)),
            put: jasmine.createSpy('put').and.returnValue(of(mockVnet)),
            delete: jasmine.createSpy('delete').and.returnValue(of(null)),
        };

        TestBed.configureTestingModule({
            providers: [
                NetworkService,
                {
                    provide: 'HTTP_CLIENT',
                    useValue: httpController,
                },
            ],
        });

        service = TestBed.inject(NetworkService);
    });

    describe('getTopology()', () => {
        it('should return topology graph data', (done) => {
            service.getTopology().subscribe((data) => {
                expect(data.nodes.length).toBe(1);
                expect((data.nodes[0].data as VirtualNetwork).name).toBe('vnet-production');
                done();
            });
        });
    });

    describe('getVnets()', () => {
        it('should return a list of virtual networks', (done) => {
            httpController.get.and.returnValue(of([mockVnet]));

            service.getVnets().subscribe((vnets) => {
                expect(Array.isArray(vnets)).toBe(true);
                expect(vnets.length).toBe(1);
                done();
            });
        });
    });

    describe('getVnet(id)', () => {
        it('should return a single VNet by ID', (done) => {
            httpController.get.and.returnValue(of(mockVnet));

            service.getVnet('vnet-1').subscribe((vnet) => {
                expect(vnet.name).toBe('vnet-production');
                done();
            });
        });
    });

    describe('createVnet(data)', () => {
        it('should create a new VNet and return it', (done) => {
            const newVnet = {
                name: 'vnet-new',
                addressSpace: '10.1.0.0/16',
                location: 'westus',
                resourceGroup: 'rg-new',
            };

            httpController.post.and.returnValue(of({ ...mockVnet, name: 'vnet-new' }));

            service.createVnet(newVnet).subscribe((vnet) => {
                expect(vnet.name).toBe('vnet-new');
                expect(httpController.post).toHaveBeenCalled();
                done();
            });
        });
    });

    describe('updateVnet(id, data)', () => {
        it('should update an existing VNet', (done) => {
            const updates = { name: 'vnet-updated' };
            httpController.put.and.returnValue(of({ ...mockVnet, ...updates }));

            service.updateVnet('vnet-1', updates).subscribe((vnet) => {
                expect(vnet.name).toBe('vnet-updated');
                expect(httpController.put).toHaveBeenCalled();
                done();
            });
        });
    });

    describe('deleteVnet(id)', () => {
        it('should delete a VNet and return confirmation', (done) => {
            httpController.delete.and.returnValue(of({}));

            service.deleteVnet('vnet-1').subscribe(() => {
                expect(httpController.delete).toHaveBeenCalledWith('/network/vnets/vnet-1');
                done();
            });
        });
    });

    describe('getSubnets(vnetId)', () => {
        it('should return subnets filtered by VNet ID', (done) => {
            const mockSubnets: Subnet[] = [
                {
                    id: 'subnet-1',
                    name: 'subnet-web',
                    addressPrefix: '10.0.1.0/24',
                    vnetId: 'vnet-1',
                },
            ];
            httpController.get.and.returnValue(of(mockSubnets));

            service.getSubnets('vnet-1').subscribe((subnets) => {
                expect(subnets.length).toBe(1);
                expect(subnets[0].name).toBe('subnet-web');
                done();
            });
        });
    });

    describe('createSubnet(data)', () => {
        it('should create a new subnet and return it', (done) => {
            const newSubnet: Subnet = {
                id: 'subnet-new',
                name: 'subnet-app',
                addressPrefix: '10.0.2.0/24',
                vnetId: 'vnet-1',
            };

            httpController.post.and.returnValue(of(newSubnet));

            service.createSubnet(newSubnet).subscribe((subnet) => {
                expect(subnet.name).toBe('subnet-app');
                done();
            });
        });
    });

    describe('deleteSubnet(id)', () => {
        it('should delete a subnet', (done) => {
            httpController.delete.and.returnValue(of({}));

            service.deleteSubnet('subnet-1').subscribe(() => {
                expect(httpController.delete).toHaveBeenCalledWith('/network/subnets/subnet-1');
                done();
            });
        });
    });

    describe('getNsgs()', () => {
        it('should return a list of NSGs', (done) => {
            const mockNsgs: NetworkSecurityGroup[] = [
                {
                    id: 'nsg-1',
                    name: 'nsg-web',
                    location: 'eastus',
                    vnetId: 'vnet-1',
                    resourceGroup: 'rg-web',
                    syncStatus: SyncStatus.APPLIED,
                    rules: [],
                    subnets: [],
                    connections: [],
                },
            ];
            httpController.get.and.returnValue(of(mockNsgs));

            service.getNsgs().subscribe((nsgs) => {
                expect(nsgs.length).toBe(1);
                expect(nsgs[0].name).toBe('nsg-web');
                done();
            });
        });
    });

    describe('createNsg(data)', () => {
        it('should create a new NSG', (done) => {
            const newNsg = {
                name: 'nsg-new',
                location: 'eastus',
                vnetId: 'vnet-1',
                resourceGroup: 'rg-new',
            };

            httpController.post.and.returnValue(of({ ...newNsg, id: 'nsg-new' }));

            service.createNsg(newNsg).subscribe((nsg) => {
                expect(nsg.name).toBe('nsg-new');
                done();
            });
        });
    });

    describe('deleteNsg(id)', () => {
        it('should delete an NSG', (done) => {
            httpController.delete.and.returnValue(of({}));

            service.deleteNsg('nsg-1').subscribe(() => {
                expect(httpController.delete).toHaveBeenCalledWith('/network/nsgs/nsg-1');
                done();
            });
        });
    });

    describe('getExternalDevices()', () => {
        it('should return a list of external devices', (done) => {
            const mockDevices: ExternalNetworkDevice[] = [
                {
                    id: 'ext-1',
                    name: 'vpn-appliance',
                    ipAddress: '1.2.3.4',
                    deviceType: DeviceType.ROUTER,
                    vendor: 'Palo Alto',
                },
            ];
            httpController.get.and.returnValue(of(mockDevices));

            service.getExternalDevices().subscribe((devices) => {
                expect(devices.length).toBe(1);
                expect(devices[0].name).toBe('vpn-appliance');
                done();
            });
        });
    });

    describe('getConnections(filters)', () => {
        it('should return connections with optional filters', (done) => {
            const mockConnections: NetworkConnection[] = [
                {
                    id: 'conn-1',
                    sourceId: 'ext-1',
                    sourceType: 'external_device',
                    destinationId: 'vnet-1',
                    destinationType: 'virtual_network',
                    connectionType: ConnectionType.VPN,
                },
            ];
            httpController.get.and.returnValue(of(mockConnections));

            service.getConnections({ connectionType: ConnectionType.VPN }).subscribe((connections) => {
                expect(connections.length).toBe(1);
                done();
            });
        });
    });

    describe('createConnection(data)', () => {
        it('should create a new network connection', (done) => {
            const newConn: NetworkConnection = {
                id: 'conn-new',
                sourceId: 'ext-1',
                sourceType: 'external_device',
                destinationId: 'vnet-1',
                destinationType: 'virtual_network',
                connectionType: ConnectionType.VPN,
            };

            httpController.post.and.returnValue(of(newConn));

            service.createConnection(newConn).subscribe((conn) => {
                expect(conn.id).toBe('conn-new');
                done();
            });
        });
    });

    describe('deleteConnection(id)', () => {
        it('should delete a network connection', (done) => {
            httpController.delete.and.returnValue(of({}));

            service.deleteConnection('conn-1').subscribe(() => {
                expect(httpController.delete).toHaveBeenCalledWith('/network/connections/conn-1');
                done();
            });
        });
    });
});